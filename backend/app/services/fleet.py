"""
Urban Butterfly - Flotte (registry des véhicules du commandement)

Chaque agence (SAMU, dépôts municipaux, protection civile) pousse ses
faits vers /integration/fleet-updates. Ce service fait vivre le registre :
matricules, types, statuts, positions. Le dispatch puise ici.
"""

import math
from datetime import datetime, timedelta, timezone

from app.db.mongo_client import mongo_client
from app.db.neo4j_client import neo4j_client

# flotte de départ (jouée par le simulateur de sources en démo)
SEED_FLEET = [
    {"callsign": "SAMU-9", "type": "AMBULANCE", "base_id": "W1"},
    {"callsign": "SAMU-12", "type": "AMBULANCE", "base_id": "W2"},
    {"callsign": "SAMU-17", "type": "AMBULANCE", "base_id": "W3"},
    {"callsign": "TIR-15", "type": "SUPPLY", "base_id": "W2"},
    {"callsign": "TIR-21", "type": "SUPPLY", "base_id": "W3"},
    {"callsign": "PAT-4", "type": "NORMAL", "base_id": "W3"},
]


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _iso(dt) -> str:
    return dt.isoformat()


def _base_coords():
    rows = neo4j_client.query(
        "MATCH (n:Infrastructure) WHERE n.lat IS NOT NULL "
        "RETURN n.id AS id, n.lat AS lat, n.lon AS lon"
    )
    return {r["id"]: [r["lat"], r["lon"]] for r in rows}


CENTER = [36.8, 10.17]  # barycentre Grand Tunis

def ensure_fleet() -> int:
    """Peuple le registre au premier appel (idempotent)."""
    if mongo_client.count_vehicles() > 0:
        return mongo_client.count_vehicles()
    coords = _base_coords()
    for spec in SEED_FLEET:
        mongo_client.insert_vehicle({
            **spec,
            "status": "AVAILABLE",
            "position": coords.get(spec["base_id"], CENTER),
            "mission_id": None,
            "registered_at": _iso(_now()),
        })
    return mongo_client.count_vehicles()


def list_fleet() -> list[dict]:
    ensure_fleet()
    _tick_retours()
    out = []
    for v in mongo_client.list_vehicles():
        v = dict(v)
        v.pop("_id", None)
        out.append(v)
    return out


def integrate_fleet_update(payload: dict) -> dict:
    """
    Une agence pousse l'état de son véhicule :
        {"callsign": "SAMU-9", "type": "AMBULANCE", "base_id": "W1",
         "status": "DEPARTED", "position": [36.78, 10.20], "mission_id": "M-08"}
    Statuts connus : AVAILABLE, DEPARTED, ON_MISSION, ARRIVED, OUT_OF_SERVICE.
    Le registre fusionne — le commandement ne tape rien.
    """
    callsign = (payload.get("callsign") or "").upper().strip()
    if not callsign:
        raise ValueError("callsign obligatoire")

    coords = _base_coords()
    fields = {}
    if payload.get("type"):
        fields["type"] = payload["type"]
    if payload.get("base_id"):
        fields["base_id"] = payload["base_id"].upper()
        fields.setdefault("position", coords.get(fields["base_id"], []))
    if payload.get("position"):
        fields["position"] = payload["position"][:2]
    if payload.get("status"):
        status = payload["status"].upper()
        if status not in ("AVAILABLE", "DEPARTED", "ON_MISSION", "ARRIVED", "OUT_OF_SERVICE"):
            raise ValueError(f"status inconnu : {status}")
        fields["status"] = "ON_MISSION" if status == "DEPARTED" else status
    if "mission_id" in payload:
        fields["mission_id"] = payload["mission_id"]
    if not fields:
        raise ValueError("aucun champ à fusionner")

    # Réception d'agence seulement : les mouvements calculés et le seed ne
    # doivent jamais faire croire qu'un partenaire a transmis une donnée.
    fields["agency_received_at"] = _now()

    # Un retour d'agence ne doit pas effacer une reservation de dispatch.
    if fields.get("status") == "AVAILABLE":
        result = mongo_client._db.vehicles.update_one(
            {"callsign": callsign, "status": {"$ne": "RESERVED"}},
            {"$set": fields}, upsert=False,
        )
        if not result.matched_count:
            # Même si AVAILABLE est ignoré pendant une réservation, la donnée
            # externe a bien été reçue : ne dater que cette réception.
            existing = mongo_client._db.vehicles.update_one(
                {"callsign": callsign}, {"$set": {"agency_received_at": fields["agency_received_at"]}},
            )
            if not existing.matched_count:
                mongo_client.insert_vehicle({"callsign": callsign, **fields})
    else:
        mongo_client.upsert_vehicle(callsign, fields)
    return {"callsign": callsign, **fields}


def available(type_needed: str | None = None) -> list[dict]:
    vehicles = [
        v for v in mongo_client.list_vehicles()
        if v["status"] == "AVAILABLE"
        and (type_needed is None or v["type"] == type_needed)
    ]
    return vehicles


def reserve(callsign: str, call_id: str) -> bool:
    return mongo_client.reserve_vehicle(callsign, call_id)


def assign(callsign: str, mission_id: str, call_id: str) -> bool:
    return mongo_client.commit_vehicle(callsign, call_id, mission_id)


def cancel_reservation(callsign: str, call_id: str):
    mongo_client.cancel_vehicle_reservation(callsign, call_id)


def _haversine_km(a: list[float], b: list[float]) -> float:
    lat1, lon1, lat2, lon2 = a[0], a[1], b[0], b[1]
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    x = (
        math.sin(dlat / 2) ** 2
        + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2) ** 2
    )
    return 6371.0 * 2 * math.asin(math.sqrt(x))


def release(mission_id: str, position: list[float] | None = None, status: str = "AVAILABLE"):
    v = next((v for v in mongo_client.list_vehicles() if v.get("mission_id") == mission_id), None)
    if not v:
        return None
    fields = {"status": status, "mission_id": None}
    if position:
        fields["position"] = position
    if status == "RETURNING" and position:
        # le convoi regagne sa base : duree ~ 1 min/km, bornee 30 s - 4 min
        coords = _base_coords()
        base = coords.get(v.get("base_id"), CENTER)
        km = _haversine_km(position, base)
        duree = max(30.0, min(240.0, km * 60.0))
        now = _now()
        fields["return_started"] = _iso(now)
        fields["return_until"] = _iso(now + timedelta(seconds=duree))
        fields["return_from"] = position
    mongo_client.upsert_vehicle(v["callsign"], fields)
    return v["callsign"]


def _tick_retours():
    """Fait avancer les vehicules en retour de base vers leur depot."""
    now = _now()
    coords = _base_coords()
    for v in mongo_client.list_vehicles():
        if v.get("status") != "RETURNING":
            continue
        try:
            until = datetime.fromisoformat(v["return_until"])
            started = datetime.fromisoformat(v["return_started"])
        except (KeyError, TypeError, ValueError):
            # donnees incoherentes : remise dispo immediate
            mongo_client.upsert_vehicle(v["callsign"], {
                "status": "AVAILABLE", "mission_id": None,
                "return_until": None, "return_started": None, "return_from": None,
            })
            continue
        if until.tzinfo is None:
            until = until.replace(tzinfo=timezone.utc)
        if started.tzinfo is None:
            started = started.replace(tzinfo=timezone.utc)
        base = coords.get(v.get("base_id"), CENTER)
        if now >= until:
            mongo_client.upsert_vehicle(v["callsign"], {
                "status": "AVAILABLE", "position": base, "mission_id": None,
                "return_until": None, "return_started": None, "return_from": None,
            })
            continue
        total = max(1.0, (until - started).total_seconds())
        progres = 1.0 - (until - now).total_seconds() / total
        depart = v.get("return_from") or v.get("position") or base
        position = [
            depart[0] + (base[0] - depart[0]) * progres,
            depart[1] + (base[1] - depart[1]) * progres,
        ]
        mongo_client.upsert_vehicle(v["callsign"], {"position": position})
