"""
Urban Butterfly - Dispatcher automatique (standard de crise)

Un appel entrant (pousse par le CACU via /integration/calls) est pris en
charge IMMEDIATEMENT :
    1. verifier la destination
    2. choisir le vehicule disponible le plus proche (haversine)
    3. creer la mission (le moteur de routage calcule l'itineraire optimal)
    4. marquer le vehicule EN MISSION

L'operateur ne saisit rien : le systeme vit de ce qu'il recoit.
"""

import math
import threading
from datetime import datetime, timezone

from app.db.mongo_client import mongo_client
from app.db.neo4j_client import neo4j_client
from app.services import fleet
from app.services.missions import create_mission

# le type d'urgence conduit au type de mission
MEDICAL = "MEDICAL"
SUPPLY = "SUPPLY"

# ----- file d'attente des appels sans vehicule -----
FILE_EVERY = 15        # secondes entre deux tentatives de rappel
FILE_MAX_TRIES = 16    # ~4 min : couvre la fenetre max de retour a base

_file_thread = None
_file_stop = threading.Event()


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _iso(dt) -> str:
    return dt.isoformat()


def _coords_of(node_id: str) -> list[float]:
    rows = neo4j_client.query(
        "MATCH (n:Infrastructure {id: $id}) RETURN n.lat AS lat, n.lon AS lon",
        {"id": node_id},
    )
    if not rows or rows[0]["lat"] is None:
        raise LookupError(f"destination {node_id} inconnue ou sans position GPS")
    return [rows[0]["lat"], rows[0]["lon"]]


def _distance_km(a: list[float], b: list[float]) -> float:
    lat1, lon1, lat2, lon2 = a[0], a[1], b[0], b[1]
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    x = (
        math.sin(dlat / 2) ** 2
        + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2) ** 2
    )
    return 6371.0 * 2 * math.asin(math.sqrt(x))


def profile_for(kind: str) -> str:
    return {"MEDICAL": "AMBULANCE", "SUPPLY": "SUPPLY"}.get(kind, "NORMAL")


def _choisir_vehicule(profile: str, coords: list[float], destination_id: str):
    """Vehicule dispo le plus proche, sans jamais partir pour aller a sa base."""
    candidates = fleet.available(None)
    typed = [v for v in candidates if v["type"] == profile]
    pool = typed or candidates
    if not pool:
        return None

    def veh_ref(v):
        ref = v.get("position") or []
        if len(ref) != 2:
            try:
                ref = _coords_of(v["base_id"])
            except (LookupError, RuntimeError):
                ref = [36.80, 10.17]
        return _distance_km(ref, coords)

    chosen = sorted(pool, key=veh_ref)[0]
    for v in sorted(pool, key=veh_ref):
        if v.get("base_id") != destination_id:
            chosen = v
            break
    return chosen


def _envoyer(call: dict, chosen: dict) -> dict:
    profile = profile_for(call["kind"])
    mission = create_mission(
        origin_id=chosen["base_id"],
        destination_id=call["destination_id"],
        profile=profile,
        caller_note=call.get("note", ""),
        vehicle=chosen["callsign"],
    )
    fleet.assign(chosen["callsign"], mission["mission_id"])
    return mission


def create_call(kind: str, destination_id: str, note: str = "") -> dict:
    """L'appel arrive ; le dispatcher le traite tout de suite."""
    kind = (kind or MEDICAL).upper()
    if kind not in (MEDICAL, SUPPLY):
        kind = MEDICAL
    destination_id = destination_id.upper().strip()
    coords = _coords_of(destination_id)

    profile = profile_for(kind)
    call_id = f"A-{mongo_client.sequence('appel', 'calls', 'call_id'):03d}"
    call = {
        "call_id": call_id,
        "kind": kind,
        "destination_id": destination_id,
        "note": note,
        "status": "PENDING",
        "created_at": _iso(_now()),
    }

    chosen = _choisir_vehicule(profile, coords, destination_id)
    if chosen is None:
        # flotte saturee : l'appel PATIENTE dans la file, le dispatcher
        # reessaie automatiquement des qu'un vehicule se libere
        call["queue_tries"] = 0
        mongo_client.insert_call(call)
        call.pop("_id", None)
        return call

    mission = _envoyer(call, chosen)

    call["status"] = "DISPATCHED"
    call["assigned_vehicle"] = chosen["callsign"]
    call["mission_id"] = mission["mission_id"]
    mongo_client.insert_call(call)
    call.pop("_id", None)
    return call


def list_calls(limit: int = 12) -> list[dict]:
    out = []
    for c in mongo_client.list_calls(limit):
        c = dict(c)
        c.pop("_id", None)
        out.append(c)
    return out


def _file_traiter():
    """Reessaye les appels PENDING : envoyer ou classer NO_VEHICLE."""
    for doc in mongo_client._db.calls.find({"status": "PENDING"}):
        call = dict(doc)
        call.pop("_id", None)
        tries = call.get("queue_tries", 0) + 1
        try:
            coords = _coords_of(call["destination_id"])
        except (LookupError, RuntimeError):
            # destination injoignable : appel classe sans vehicule
            mongo_client._db.calls.update_one(
                {"call_id": call["call_id"]},
                {"$set": {"status": "NO_VEHICLE",
                          "note": "destination injoignable"}},
            )
            continue
        chosen = _choisir_vehicule(profile_for(call["kind"]), coords,
                                   call["destination_id"])
        if chosen is None:
            if tries >= FILE_MAX_TRIES:
                mongo_client._db.calls.update_one(
                    {"call_id": call["call_id"]},
                    {"$set": {"status": "NO_VEHICLE", "queue_tries": tries}},
                )
                print(f"[dispatcher] appel {call['call_id']} classe "
                      "NO_VEHICLE (file saturee)")
            else:
                mongo_client._db.calls.update_one(
                    {"call_id": call["call_id"]}, {"$set": {"queue_tries": tries}}
                )
            continue
        try:
            mission = _envoyer(call, chosen)
        except Exception as exc:
            print(f"[dispatcher] rappel {call['call_id']} rate : {exc}")
            mongo_client._db.calls.update_one(
                {"call_id": call["call_id"]}, {"$set": {"queue_tries": tries}}
            )
            continue
        mongo_client._db.calls.update_one(
            {"call_id": call["call_id"]},
            {"$set": {
                "status": "DISPATCHED",
                "assigned_vehicle": chosen["callsign"],
                "mission_id": mission["mission_id"],
                "dispatched_at": _iso(_now()),
                "queue_tries": tries,
            }},
        )
        print(f"[dispatcher] file d'attente : {call['call_id']} envoye avec "
              f"{chosen['callsign']} (essai {tries})")


def _file_loop():
    while not _file_stop.wait(FILE_EVERY):
        try:
            _file_traiter()
        except Exception as exc:
            print(f"[dispatcher] file d'attente : {exc}")


def start_queue():
    """Demarre la boucle de rappel des appels en attente."""
    global _file_thread
    if _file_thread and _file_thread.is_alive():
        return
    _file_stop.clear()
    _file_thread = threading.Thread(target=_file_loop, daemon=True,
                                    name="file-appels")
    _file_thread.start()


def random_call() -> dict:
    """Le simulateur de sources : un appel 15/191 arrive, adresse aleatoire."""
    import random

    targets = neo4j_client.query(
        "MATCH (n:Infrastructure) WHERE n.kind IN ['Hospital','Pharmacy','Warehouse'] "
        "AND n.lat IS NOT NULL RETURN n.id AS id, n.kind AS kind"
    )
    if not targets:
        raise RuntimeError("aucune cible valide pour un appel")
    dest = random.choice(targets)
    kind = MEDICAL if dest["kind"] in ("Hospital", "Pharmacy") else SUPPLY
    notes = {
        MEDICAL: ["Accident de la circulation", "Malaise — personne au sol",
                  "Brûlure — urgence modérée", "Urgence respiratoire"],
        SUPPLY: ["Ravitaillement urgent", "Réassort antigel / sérum",
                 "Livraison oxygène médical"],
    }
    return create_call(kind, dest["id"], random.choice(notes[kind]))
