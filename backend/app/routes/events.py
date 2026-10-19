from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException

from app.db.mongo_client import mongo_client
from app.db.neo4j_client import neo4j_client
from app.models.event import EventCreate
from app.models.impact import ImpactSummary
from app.services.cascade import compute_impact

router = APIRouter(prefix="/events", tags=["Events"])

STATUS_BY_EVENT_TYPE = {
    "POWER_FAILURE": "OFFLINE",
    "CYBER_ATTACK": "COMPROMISED",
    "ROAD_BLOCKED": "BLOCKED",
}

RESTORE_BY_EVENT_TYPE = {
    "POWER_FAILURE": "ONLINE",
    "CYBER_ATTACK": "ONLINE",
    "ROAD_BLOCKED": "CLEAR",
}


@router.post("", status_code=201)
def create_event(event: EventCreate):
    target = neo4j_client.query(
        "MATCH (t:Infrastructure {id: $target_id}) RETURN t.id AS id, t.kind AS kind",
        {"target_id": event.target_id},
    )
    if not target:
        raise HTTPException(404, f"target '{event.target_id}' not found in the graph")

    doc = event.model_dump()
    doc["timestamp"] = datetime.now(timezone.utc)

    mongo_result = mongo_client.insert_event(doc)
    event_id = str(mongo_result.inserted_id)

    new_status = STATUS_BY_EVENT_TYPE.get(event.type)
    if new_status:
        neo4j_client.query(
            "MATCH (t:Infrastructure {id: $target_id}) "
            "SET t.status = $status, t.last_event = $event_id",
            {"target_id": event.target_id, "status": new_status, "event_id": event_id},
        )

    neo4j_client.query(
        "CREATE (e:Event {id: $event_id, type: $type, severity: $severity, timestamp: $ts}) "
        "WITH e MATCH (t:Infrastructure {id: $target_id}) "
        "MERGE (e)-[:AFFECTS]->(t)",
        {
            "event_id": event_id,
            "type": event.type,
            "severity": event.severity,
            "ts": doc["timestamp"].isoformat(),
            "target_id": event.target_id,
        },
    )

    impact = compute_impact(event_id)
    return {"id": event_id, "stored_in": ["mongodb", "neo4j"], "impact": impact}


@router.get("")
def list_events(limit: int = 50):
    return mongo_client.list_events(limit)


@router.get("/{event_id}/impact", response_model=ImpactSummary)
def event_impact(event_id: str):
    try:
        return compute_impact(event_id)
    except LookupError as exc:
        raise HTTPException(404, str(exc))


@router.post("/{event_id}/resolve")
def resolve_event(event_id: str):
    event = mongo_client.get_event(event_id)
    if not event:
        raise HTTPException(404, f"event '{event_id}' not found in MongoDB")

    restore = RESTORE_BY_EVENT_TYPE.get(event.get("type"))

    if restore:
        neo4j_client.query(
            "MATCH (t:Infrastructure {id: $target_id}) WHERE t.last_event = $event_id "
            "SET t.status = $status REMOVE t.last_event",
            {"target_id": event["target_id"], "status": restore, "event_id": event_id},
        )

    mongo_client.set_event_status(event_id, "RESOLVED")
    return {"id": event_id, "status": "RESOLVED", "restored": restore}
