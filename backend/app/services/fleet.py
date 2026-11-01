"""
Urban Butterfly - Flotte (registry des véhicules du commandement)

Chaque agence (SAMU, dépôts municipaux, protection civile) pousse ses
faits vers /integration/fleet-updates. Ce service fait vivre le registre :
matricules, types, statuts, positions. Le dispatch puise ici.
"""

from datetime import datetime, timezone

from app.db.mongo_client import mongo_client
from app.db.neo4j_client import neo4j_client

# flotte de départ (jouée par le simulateur de sources en démo)
SEED_FLEET = [
    {"callsign": "SAMU-9", "type": "AMBULANCE", "base_id": "W1"},
    {"callsign": "SAMU-12", "type": "AMBULANCE", "base_id": "W2"},
    {"callsign": "SAMU-17", "type": "AMBULANCE", "base_id": "W3"},
    {"callsign": "TIR-15", "type": "SUPPLY", "base_id": "W2"},
    {"callsign": "TIR-21", "type": "SUPPLY", "base_id": "W3"},
    {"callsign": "PAT-4", "type": "NORMAL", "base_id": "W4"},
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

    mongo_client.upsert_vehicle(callsign, fields)
    return {"callsign": callsign, **fields}


def available(type_needed: str | None = None) -> list[dict]:
    vehicles = [
        v for v in mongo_client.list_vehicles()
        if v["status"] == "AVAILABLE"
        and (type_needed is None or v["type"] == type_needed)
    ]
    return vehicles


def assign(callsign: str, mission_id: str):
    mongo_client.upsert_vehicle(callsign, {"status": "ON_MISSION", "mission_id": mission_id})


def release(mission_id: str, position: list[float] | None = None, status: str = "AVAILABLE"):
    v = next((v for v in mongo_client.list_vehicles() if v.get("mission_id") == mission_id), None)
    if not v:
        return None
    fields = {"status": status, "mission_id": None}
    if position:
        fields["position"] = position
    mongo_client.upsert_vehicle(v["callsign"], fields)
    return v["callsign"]
