"""Boîte de réception durable des alertes de la simulation.

Une clé de source stable rend la publication idempotente ; l'accusé de prise
en compte est propre à l'alerte et ne résout jamais l'incident associé.
"""

import logging
from datetime import datetime, timezone

from bson import ObjectId
from bson.errors import InvalidId
from pymongo import ReturnDocument

from app.db.mongo_client import mongo_client

logger = logging.getLogger(__name__)

EVENT_TYPES = {
    "POWER_FAILURE": "Panne électrique",
    "CYBER_ATTACK": "Cyberattaque",
    "HEAVY_RAIN": "Pluie extrême",
    "ROAD_BLOCKED": "Route bloquée",
}


def ensure_indexes():
    mongo_client._db.notifications.create_index("source_key", unique=True)
    mongo_client._db.notifications.create_index([("created_at", -1)])


def _publish(source_key: str, category: str, severity: str, location_id: str,
             title: str, detail: str, producer: str, occurred_at=None):
    now = datetime.now(timezone.utc)
    if isinstance(occurred_at, str):
        try:
            occurred_at = datetime.fromisoformat(occurred_at)
        except ValueError:
            occurred_at = None
    if isinstance(occurred_at, datetime) and occurred_at.tzinfo is None:
        occurred_at = occurred_at.replace(tzinfo=timezone.utc)
    mongo_client._db.notifications.update_one(
        {"source_key": source_key},
        {"$setOnInsert": {
            "source_key": source_key, "category": category,
            "severity": severity, "location_id": location_id,
            "title": title, "detail": detail, "producer": producer,
            "state": "NEW", "created_at": occurred_at or now, "updated_at": now,
        }},
        upsert=True,
    )


def publish_event(event_id: str, event: dict):
    payload = event.get("payload") or {}
    description = event.get("description") or ""
    weather_observation = description.startswith("Meteo reelle zone")
    producer = ("Open-Meteo (observation météo)" if weather_observation
                else str(payload.get("source") or "simulation urbaine"))
    _publish(f"event:{event_id}", "INCIDENT", event["severity"], event["target_id"],
             EVENT_TYPES.get(event["type"], event["type"]),
             "Seuil météo observé ; incident simulé." if weather_observation
             else "Incident enregistré dans la simulation.", producer, event.get("timestamp"))


def publish_call(call: dict):
    _publish(f"call:{call['call_id']}", "CALL",
             "HIGH" if call["kind"] == "MEDICAL" else "MEDIUM",
             call["destination_id"], "Appel médical" if call["kind"] == "MEDICAL" else "Appel logistique",
             "Appel reçu par le standard simulé.", "CACU simulé", call.get("created_at"))


def publish_mission(mission: dict, status: str):
    if status not in ("ARRIVED", "BLOCKED"):
        return
    title = "Mission bloquée" if status == "BLOCKED" else "Véhicule arrivé"
    _publish(f"mission:{mission['mission_id']}:{status}", "MISSION",
             "HIGH" if status == "BLOCKED" else "LOW", mission["destination_id"],
             title, f"Mission {mission['mission_id']} · {mission.get('vehicle') or 'convoi'}.",
             "suivi de flotte simulée",
             next((item.get("at") for item in reversed(mission.get("timeline") or [])
                   if item.get("code") == ("BLOCKED" if status == "BLOCKED" else "ARRIVE")),
                  mission.get("departure_at")))


def reconcile_current():
    """Au démarrage, inclure les urgences encore ouvertes, pas le passé clos."""
    for event in mongo_client._db.events.find({"status": "ACTIVE"}):
        publish_safely(publish_event, str(event["_id"]), event)
    for call in mongo_client._db.calls.find({"status": {"$in": ["PENDING", "ROUTE_UNAVAILABLE"]}}):
        publish_safely(publish_call, call)
    for mission in mongo_client._db.missions.find({"status": "BLOCKED"}):
        publish_safely(publish_mission, mission, "BLOCKED")


def publish_safely(callback, *args):
    """Un défaut de la boîte d'alertes ne doit pas masquer une action déjà réalisée."""
    try:
        callback(*args)
    except Exception:
        logger.exception("Publication d'alerte échouée")


def resolve_event_notification(event_id: str):
    now = datetime.now(timezone.utc)
    mongo_client._db.notifications.update_one(
        {"source_key": f"event:{event_id}", "state": {"$ne": "RESOLVED"}},
        {"$set": {"state": "RESOLVED", "updated_at": now, "resolved_at": now}},
    )


def list_notifications(limit: int = 30, state: str | None = None) -> dict:
    collection = mongo_client._db.notifications
    query = {"state": state} if state else {}
    rows = collection.find(query).sort([("created_at", -1), ("_id", -1)]).limit(limit)
    counts = {name: collection.count_documents({"state": name})
              for name in ("NEW", "ACKNOWLEDGED", "RESOLVED")}
    return {"items": [_out(doc) for doc in rows], "counts": counts}


def acknowledge(notification_id: str, actor: str) -> dict | None:
    try:
        ident = ObjectId(notification_id)
    except (InvalidId, TypeError):
        return None
    now = datetime.now(timezone.utc)
    collection = mongo_client._db.notifications
    doc = collection.find_one_and_update(
        {"_id": ident, "state": "NEW"},
        {"$set": {"state": "ACKNOWLEDGED", "acknowledged_at": now,
                  "acknowledged_by": actor, "updated_at": now}},
        return_document=ReturnDocument.AFTER,
    )
    doc = doc or collection.find_one({"_id": ident})
    return _out(doc) if doc else None


def _out(doc: dict) -> dict:
    return {key: value for key, value in doc.items() if key != "_id"} | {"id": str(doc["_id"])}
