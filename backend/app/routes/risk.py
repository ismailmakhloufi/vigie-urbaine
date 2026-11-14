from fastapi import APIRouter, HTTPException

from app.db.mongo_client import mongo_client
from app.services.cascade import compute_impact
from app.services.interventions import ranked_scenarios, scenarios
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
            source = {
                "event_id": impact.event_id,
                "type": impact.event_type,
                "severity": impact.severity,
                "target_id": impact.target_id,
                "depth": node.depth,
                "score": node.score,
                "reasons": node.reasons,
                "chain": node.chain,
            }
            if current is None or node.score > current["score"]:
                replacement = node.model_dump()
                replacement["sources"] = current["sources"] + [source] if current else [source]
                replacement["main_event_id"] = impact.event_id
                nodes[node.id] = replacement
            else:
                current["sources"].append(source)

    worst = sorted(nodes.values(), key=lambda n: n["score"], reverse=True)
    for node in worst:
        node["sources"].sort(key=lambda source: (-source["score"], source["depth"], source["event_id"]))
    return {
        "active_incidents": len(event_ids),
        "incident_list": incidents,
        "nodes_at_risk": worst,
        "counts_by_class": {
            cls: sum(1 for n in worst if risk_class(n["score"]) == cls)
            for cls in ("LOW", "MEDIUM", "HIGH", "CRITICAL")
        },
    }


@router.get("/intervention/{event_id}")
def preview_resolution(event_id: str):
    """Projection en lecture seule : retirer un incident et recalculer les autres.

    Ne modifie ni les événements MongoDB, ni les statuts Neo4j, ni les missions.
    Seuls les scores du modèle de propagation sont comparés.
    """
    result = next((item for item in scenarios() if item["event_id"] == event_id), None)
    if result is None:
        raise HTTPException(404, "Cet incident n'est plus actif ou n'existe pas.")
    return result


@router.get("/decisions")
def ranked_decisions():
    """Classement de scénarios indépendants ; aucun incident n'est résolu."""
    return {"scenarios": ranked_scenarios(),
            "note": "Classement par bénéfice estimé pour les hôpitaux, puis bénéfice global. "
                    "L'accès routier utilise les véhicules disponibles et le trafic actuel ; "
                    "il n'inclut pas le temps d'intervention ni une garantie de résultat."}


@router.get("/evolution")
def risk_evolution(limit: int = 12):
    """Observations enregistrées après chaque résolution effective."""
    return mongo_client.list_risk_transitions(max(1, min(limit, 30)))
