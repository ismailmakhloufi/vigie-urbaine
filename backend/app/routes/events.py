from datetime import datetime, timezone

from bson import ObjectId
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.db.mongo_client import mongo_client
from app.db.neo4j_client import neo4j_client
from app.models.event import EventCreate

router = APIRouter(prefix="/events", tags=["Events"])

STATUS_BY_EVENT_TYPE = {
    "POWER_FAILURE": "OFFLINE",
    "CYBER_ATTACK": "COMPROMISED",
    "ROAD_BLOCKED": "BLOCKED",
}


class ImpactNode(BaseModel):
    id: str
    kind: str
    name: str
    depth: int


class ImpactSummary(BaseModel):
    event_id: str
    event_type: str
    target_id: str
    impacts: list[ImpactNode]
    direct_count: int
    total_count: int
    max_depth: int


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


@router.get("", response_model=None)
def list_events(limit: int = 50):
    return mongo_client.list_events(limit)


@router.get("/{event_id}/impact", response_model=ImpactSummary)
def event_impact(event_id: str):
    return compute_impact(event_id)


@router.post("/{event_id}/resolve")
def resolve_event(event_id: str):
    event = mongo_client.get_event(event_id)
    if not event:
        raise HTTPException(404, f"event '{event_id}' not found in MongoDB")

    if event.get("type") in ("POWER_FAILURE", "CYBER_ATTACK"):
        restore = "ONLINE"
    elif event.get("type") == "ROAD_BLOCKED":
        restore = "CLEAR"
    else:
        restore = None

    if restore:
        neo4j_client.query(
            "MATCH (t:Infrastructure {id: $target_id}) WHERE t.last_event = $event_id "
            "SET t.status = $status REMOVE t.last_event",
            {"target_id": event["target_id"], "status": restore, "event_id": event_id},
        )

    mongo_client.set_event_status(event_id, "RESOLVED")
    return {"id": event_id, "status": "RESOLVED", "restored": restore}


def compute_impact(event_id: str) -> ImpactSummary:
    head = neo4j_client.query(
        "MATCH (e:Event {id: $event_id})-[:AFFECTS]->(t) "
        "RETURN e.type AS type, t.id AS target_id",
        {"event_id": event_id},
    )
    if not head:
        raise HTTPException(404, f"event '{event_id}' has no AFFECTS link in the graph")

    event_type, target_id = head[0]["type"], head[0]["target_id"]

    if event_type == "ROAD_BLOCKED":
        rows = neo4j_client.query(
            "MATCH p = (x)-[:CONNECTED_BY*1..5]->(t:Infrastructure {id: $target_id}) "
            "RETURN x.id AS id, x.kind AS kind, x.name AS name, length(p) AS depth",
            {"target_id": target_id},
        )
    elif event_type == "HEAVY_RAIN":
        rows = neo4j_client.query(
            "MATCH (t:Infrastructure {id: $target_id})-[:LOCATED_IN]->(z)<-[:LOCATED_IN]-(r:Road) "
            "MATCH p = (x)-[:CONNECTED_BY*1..5]->(r) "
            "WHERE x <> r "
            "RETURN x.id AS id, x.kind AS kind, x.name AS name, length(p) + 1 AS depth",
            {"target_id": target_id},
        )
    else:
        rows = neo4j_client.query(
            "MATCH p = (x)-[:DEPENDS_ON*1..5]->(t:Infrastructure {id: $target_id}) "
            "RETURN x.id AS id, x.kind AS kind, x.name AS name, length(p) AS depth",
            {"target_id": target_id},
        )

    seen: dict[str, ImpactNode] = {}
    for row in rows:
        if row["id"] in seen:
            seen[row["id"]].depth = min(seen[row["id"]].depth, row["depth"])
        else:
            seen[row["id"]] = ImpactNode(**row)
    impacts = sorted(seen.values(), key=lambda n: n.depth)

    return ImpactSummary(
        event_id=event_id,
        event_type=event_type,
        target_id=target_id,
        impacts=impacts,
        direct_count=sum(1 for i in impacts if i.depth == 1),
        total_count=len(impacts),
        max_depth=max((i.depth for i in impacts), default=0),
    )
