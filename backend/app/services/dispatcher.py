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
from app.services import notifications
from app.services.missions import RouteUnavailable, create_mission

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


def _candidats(profile: str, coords: list[float], destination_id: str):
    """Véhicules disponibles ordonnés, sans partir pour aller à leur base."""
    candidates = fleet.available(None)
    typed = [v for v in candidates if v["type"] == profile]
    pool = typed or candidates
    if not pool:
        return []

    def veh_ref(v):
        ref = v.get("position") or []
        if len(ref) != 2:
            try:
                ref = _coords_of(v["base_id"])
            except (LookupError, RuntimeError):
                ref = [36.80, 10.17]
        return _distance_km(ref, coords)

    ordered = sorted(pool, key=veh_ref)
    return [v for v in ordered if v.get("base_id") != destination_id] or ordered


def _envoyer(call: dict, chosen: dict) -> dict:
    profile = profile_for(call["kind"])
    mission = create_mission(
        origin_id=chosen["base_id"],
        destination_id=call["destination_id"],
        profile=profile,
        caller_note=call.get("note", ""),
        vehicle=chosen["callsign"],
        call_id=call["call_id"],
    )
    if not fleet.assign(chosen["callsign"], mission["mission_id"], call["call_id"]):
        # Ne jamais laisser une mission active sans propriétaire.
        mongo_client._db.missions.delete_one({"mission_id": mission["mission_id"]})
        raise RuntimeError("réservation de véhicule perdue avant le départ")
    return mission


def _dispatch(call: dict, coords: list[float]) -> tuple[str, dict | None, dict | None]:
    """Essaie chaque véhicule : réservation atomique avant routage et écriture."""
    candidates = _candidats(profile_for(call["kind"]), coords, call["destination_id"])
    reserved = False
    route_failed = False
    for chosen in candidates:
        if not fleet.reserve(chosen["callsign"], call["call_id"]):
            continue
        reserved = True
        try:
            mission = _envoyer(call, chosen)
            return "DISPATCHED", chosen, mission
        except RouteUnavailable as exc:
            route_failed = True
            print(f"[dispatcher] itinéraire {chosen['callsign']} indisponible : {exc}")
        finally:
            fleet.cancel_reservation(chosen["callsign"], call["call_id"])
    return ("ROUTE_UNAVAILABLE" if route_failed and reserved else "PENDING"), None, None


def create_call(kind: str, destination_id: str, note: str = "") -> dict:
    """L'appel arrive ; le dispatcher le traite tout de suite."""
    kind = (kind or MEDICAL).upper()
    if kind not in (MEDICAL, SUPPLY):
        kind = MEDICAL
    destination_id = destination_id.upper().strip()
    coords = _coords_of(destination_id)

    call_id = f"A-{mongo_client.sequence('appel', 'calls', 'call_id'):03d}"
    call = {
        "call_id": call_id,
        "kind": kind,
        "destination_id": destination_id,
        "note": note,
        "status": "PENDING",
        "created_at": _iso(_now()),
        "queue_tries": 0,
    }

    mongo_client.insert_call(call)
    notifications.publish_safely(notifications.publish_call, call)
    status, chosen, mission = _dispatch(call, coords)
    call["status"] = status
    if mission:
        call["assigned_vehicle"] = chosen["callsign"]
        call["mission_id"] = mission["mission_id"]
    elif status == "ROUTE_UNAVAILABLE":
        call["queue_reason"] = "destination momentanément inaccessible par la route"
    else:
        call["queue_reason"] = "aucun véhicule disponible"
    mongo_client.update_call(call_id, {key: value for key, value in call.items()
                                       if key not in ("_id", "call_id")})
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
    """Reessaie la flotte saturée (borné) et les routes bloquées (non borné)."""
    for doc in mongo_client._db.calls.find({"status": {"$in": ["PENDING", "ROUTE_UNAVAILABLE"]}}):
        call = dict(doc)
        call.pop("_id", None)
        existing = mongo_client._db.missions.find_one({"call_id": call["call_id"]})
        if existing:
            mongo_client.update_call(call["call_id"], {
                "status": "DISPATCHED", "assigned_vehicle": existing["vehicle"],
                "mission_id": existing["mission_id"], "queue_reason": None,
            })
            continue
        try:
            coords = _coords_of(call["destination_id"])
        except (LookupError, RuntimeError):
            mongo_client.update_call(call["call_id"], {"status": "ROUTE_UNAVAILABLE",
                "queue_reason": "destination momentanément inaccessible"})
            continue
        try:
            status, chosen, mission = _dispatch(call, coords)
        except Exception as exc:
            print(f"[dispatcher] rappel {call['call_id']} raté : {exc}")
            continue
        if status == "PENDING":
            tries = call.get("queue_tries", 0) + 1
            if tries >= FILE_MAX_TRIES:
                mongo_client.update_call(call["call_id"], {"status": "NO_VEHICLE",
                    "queue_tries": tries, "queue_reason": "flotte indisponible après plusieurs essais"})
                print(f"[dispatcher] appel {call['call_id']} classe "
                      "NO_VEHICLE (file saturee)")
            else:
                mongo_client.update_call(call["call_id"], {"status": "PENDING",
                    "queue_tries": tries, "queue_reason": "aucun véhicule disponible"})
            continue
        if status == "ROUTE_UNAVAILABLE":
            mongo_client.update_call(call["call_id"], {"status": status, "queue_tries": 0,
                "queue_reason": "destination momentanément inaccessible par la route"})
            continue
        mongo_client.update_call(call["call_id"], {
                "status": "DISPATCHED",
                "assigned_vehicle": chosen["callsign"],
                "mission_id": mission["mission_id"],
                "dispatched_at": _iso(_now()),
                "queue_reason": None,
            })
        print(f"[dispatcher] file d'attente : {call['call_id']} envoye avec "
              f"{chosen['callsign']}")


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
    recover_reservations()
    _file_stop.clear()
    _file_thread = threading.Thread(target=_file_loop, daemon=True,
                                    name="file-appels")
    _file_thread.start()


def stop_queue():
    """Arrête les relances automatiques lorsque l'opérateur stoppe la simulation."""
    _file_stop.set()
    if _file_thread and _file_thread.is_alive():
        _file_thread.join(timeout=3)


def recover_reservations():
    """Après un arrêt au milieu du routage, achever ou annuler les réservations."""
    for vehicle in mongo_client._db.vehicles.find({"status": "RESERVED"}):
        call_id = vehicle.get("reservation")
        callsign = vehicle["callsign"]
        mission = mongo_client._db.missions.find_one({"call_id": call_id, "vehicle": callsign})
        if mission:
            if fleet.assign(callsign, mission["mission_id"], call_id):
                mongo_client.update_call(call_id, {
                    "status": "DISPATCHED", "assigned_vehicle": callsign,
                    "mission_id": mission["mission_id"], "queue_reason": None,
                })
        else:
            fleet.cancel_reservation(callsign, call_id)


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
