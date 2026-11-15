"""Instantanés observés pour une relecture strictement en lecture seule.

On conserve les résultats calculés *au moment de la capture* : rejouer le
graphe actuel sur un ancien incident réécrirait l'histoire. Les lectures entre
Mongo et Neo4j ne sont pas transactionnelles ; la fenêtre de capture est
exposée afin de ne pas prétendre à une simultanéité parfaite.
"""

import logging
import threading
from datetime import datetime, timezone

from bson import BSON, ObjectId
from bson.errors import InvalidId

from app.db.mongo_client import mongo_client

logger = logging.getLogger(__name__)
EVERY_SECONDS = 30
RETENTION_SECONDS = 24 * 60 * 60
MAX_BYTES = 8 * 1024 * 1024
_thread = None
_stop = threading.Event()


def capture() -> dict:
    """Lecture seule sur les données de crise ; seul le document d'archive est écrit."""
    from app.routes.infra import infrastructure
    from app.routes.risk import risk_overview

    started = datetime.now(timezone.utc)
    risk = risk_overview()
    statuses = {item["id"]: item.get("status") for item in infrastructure()}
    vehicles = [{key: v.get(key) for key in ("callsign", "type", "status", "base_id", "mission_id", "position")}
                for v in mongo_client.list_vehicles()]
    missions = [{key: m.get(key) for key in ("mission_id", "status", "vehicle", "origin_id", "destination_id")}
                for m in mongo_client._db.missions.find({}, {"_id": 0}).sort("departure_at", -1).limit(30)]
    calls = [{key: c.get(key) for key in ("call_id", "status", "kind", "destination_id", "assigned_vehicle", "queue_reason")}
             for c in mongo_client.list_calls(15)]
    doc = {"captured_at": datetime.now(timezone.utc), "started_at": started,
           "risk": risk, "infrastructure_status": statuses, "vehicles": vehicles,
           "missions": missions, "calls": calls, "schema_version": 1,
           "consistency": "best_effort"}
    if len(BSON.encode(doc)) > MAX_BYTES:
        raise RuntimeError("Instantané trop volumineux : archive non enregistrée")
    result = mongo_client._db.crisis_snapshots.insert_one(doc)
    return {"id": str(result.inserted_id), "captured_at": doc["captured_at"]}


def list_snapshots(limit: int = 120, before: datetime | None = None) -> list[dict]:
    query = {"captured_at": {"$lt": before}} if before else {}
    rows = mongo_client._db.crisis_snapshots.find(query, {
        "captured_at": 1, "started_at": 1, "risk.active_incidents": 1,
        "risk.counts_by_class": 1, "schema_version": 1,
    }).sort("captured_at", -1).limit(max(1, min(limit, 500)))
    return [{"id": str(row["_id"]), "captured_at": row["captured_at"],
             "started_at": row["started_at"], "active_incidents": row["risk"]["active_incidents"],
             "counts_by_class": row["risk"]["counts_by_class"]} for row in rows]


def get_snapshot(snapshot_id: str) -> dict | None:
    try:
        ident = ObjectId(snapshot_id)
    except (InvalidId, TypeError):
        return None
    doc = mongo_client._db.crisis_snapshots.find_one({"_id": ident}, {"_id": 0})
    return doc


def _loop():
    while not _stop.is_set():
        try:
            capture()
        except Exception:
            logger.exception("Capture de crise indisponible ; prochain essai dans 30 secondes")
        if _stop.wait(EVERY_SECONDS):
            break


def start_recorder():
    global _thread
    if _thread and _thread.is_alive():
        return
    mongo_client._db.crisis_snapshots.create_index("captured_at", expireAfterSeconds=RETENTION_SECONDS)
    _stop.clear()
    _thread = threading.Thread(target=_loop, name="ub-relecture", daemon=True)
    _thread.start()


def stop_recorder():
    _stop.set()
    if _thread and _thread.is_alive():
        _thread.join(timeout=5)
