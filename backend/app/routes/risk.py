from fastapi import APIRouter

from app.db.mongo_client import mongo_client
from app.services.cascade import compute_impact
from app.services.risk import risk_class

router = APIRouter(prefix="/risk", tags=["Risk"])


@router.get("")
def risk_overview():
    event_ids = mongo_client.get_active_events()

    nodes: dict[str, dict] = {}
    incidents = []
    for event_id in event_ids:
        impact = compute_impact(event_id)
        incidents.append(
            {
                "event_id": impact.event_id,
                "type": impact.event_type,
                "severity": impact.severity,
                "target_id": impact.target_id,
                "total_count": impact.total_count,
                "max_depth": impact.max_depth,
            }
        )
        for node in impact.impacts:
            current = nodes.get(node.id)
            if current is None or node.score > current["score"]:
                nodes[node.id] = node.model_dump()

    worst = sorted(nodes.values(), key=lambda n: n["score"], reverse=True)
    return {
        "active_incidents": len(event_ids),
        "incident_list": incidents,
        "nodes_at_risk": worst,
        "counts_by_class": {
            cls: sum(1 for n in worst if risk_class(n["score"]) == cls)
            for cls in ("LOW", "MEDIUM", "HIGH", "CRITICAL")
        },
    }
