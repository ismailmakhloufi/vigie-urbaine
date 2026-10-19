"""
Cascade Engine v0 : calcule la propagation d'un evenement et le
score de risque de chaque noeud touche (section 11 + 13 du CSC).
"""

from app.core.config import get_settings
from app.db.mongo_client import mongo_client
from app.db.neo4j_client import neo4j_client
from app.models.impact import ImpactNode, ImpactSummary
from app.services.risk import risk_class, score_node


def _active_incidents() -> int:
    return mongo_client.count_active_events()


def _propagation_rows(event_type: str, target_id: str):
    if event_type == "ROAD_BLOCKED":
        return neo4j_client.query(
            "MATCH p = (x)-[:CONNECTED_BY*1..5]->(t:Infrastructure {id: $target_id}) "
            "RETURN x.id AS id, x.kind AS kind, x.name AS name, length(p) AS depth, "
            "x.criticality AS criticality, x.backup_power_hours AS backup_power_hours",
            {"target_id": target_id},
        )
    if event_type == "HEAVY_RAIN":
        return neo4j_client.query(
            "MATCH (t:Infrastructure {id: $target_id})-[:LOCATED_IN]->(z)"
            "<-[:LOCATED_IN]-(r:Road) "
            "MATCH p = (x)-[:CONNECTED_BY*1..5]->(r) "
            "WHERE x <> r "
            "RETURN x.id AS id, x.kind AS kind, x.name AS name, length(p) + 1 AS depth, "
            "x.criticality AS criticality, x.backup_power_hours AS backup_power_hours",
            {"target_id": target_id},
        )
    return neo4j_client.query(
        "MATCH p = (x)-[:DEPENDS_ON*1..5]->(t:Infrastructure {id: $target_id}) "
        "RETURN x.id AS id, x.kind AS kind, x.name AS name, length(p) AS depth, "
        "x.criticality AS criticality, x.backup_power_hours AS backup_power_hours",
        {"target_id": target_id},
    )


def compute_impact(event_id: str) -> ImpactSummary:
    head = neo4j_client.query(
        "MATCH (e:Event {id: $event_id})-[:AFFECTS]->(t) "
        "RETURN e.type AS type, e.severity AS severity, t.id AS target_id",
        {"event_id": event_id},
    )
    if not head:
        raise LookupError(f"event '{event_id}' has no AFFECTS link in the graph")

    event_type, severity, target_id = (
        head[0]["type"],
        head[0]["severity"],
        head[0]["target_id"],
    )

    rows = _propagation_rows(event_type, target_id)
    incidents = _active_incidents()

    seen: dict[str, ImpactNode] = {}
    for row in rows:
        node_id = row["id"]
        depth = row["depth"]
        if node_id in seen:
            seen[node_id].depth = min(seen[node_id].depth, depth)
        else:
            score, reasons = score_node(
                depth=min(depth, 2),
                criticality=row["criticality"] or 0,
                backup_power_hours=row["backup_power_hours"] if row["backup_power_hours"] is not None else 0,
                severity=severity,
                active_incidents=incidents,
            )
            seen[node_id] = ImpactNode(
                id=node_id,
                kind=row["kind"],
                name=row["name"],
                depth=depth,
                score=score,
                risk=risk_class(score),
                reasons=reasons,
            )
    impacts = sorted(seen.values(), key=lambda n: n.depth)

    return ImpactSummary(
        event_id=event_id,
        event_type=event_type,
        severity=severity,
        target_id=target_id,
        impacts=impacts,
        direct_count=sum(1 for i in impacts if i.depth == 1),
        total_count=len(impacts),
        max_depth=max((i.depth for i in impacts), default=0),
    )
