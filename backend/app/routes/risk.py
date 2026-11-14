from fastapi import APIRouter, HTTPException

from app.db.mongo_client import mongo_client
from app.services.cascade import compute_impact
from app.services.risk import risk_class

router = APIRouter(prefix="/risk", tags=["Risk"])


def _scores(impacts) -> dict[str, dict]:
    """Même règle que la vue générale : le score le plus élevé gagne."""
    nodes: dict[str, dict] = {}
    for impact in impacts:
        for node in impact.impacts:
            if node.id not in nodes or node.score > nodes[node.id]["score"]:
                nodes[node.id] = node.model_dump()
    return nodes


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
    event_ids = mongo_client.get_active_events()
    if event_id not in event_ids:
        raise HTTPException(404, "Cet incident n'est plus actif ou n'existe pas.")

    active_count = mongo_client.count_active_events()
    avant_impacts = [compute_impact(eid, active_incidents=active_count) for eid in event_ids]
    apres_impacts = [compute_impact(eid, active_incidents=max(0, active_count - 1))
                     for eid in event_ids if eid != event_id]
    avant = _scores(avant_impacts)
    apres = _scores(apres_impacts)
    evenement = next(impact for impact in avant_impacts if impact.event_id == event_id)

    changements = []
    for ident, node in avant.items():
        score_apres = apres.get(ident, {}).get("score", 0)
        changements.append({
            "id": ident,
            "name": node["name"],
            "kind": node["kind"],
            "before": node["score"],
            "after": score_apres,
            "reduction": node["score"] - score_apres,
            "risk_before": risk_class(node["score"]),
            "risk_after": risk_class(score_apres) if score_apres else None,
        })
    changements.sort(key=lambda n: (-n["reduction"], -n["before"], n["id"]))
    return {
        "event_id": event_id,
        "event_type": evenement.event_type,
        "target_id": evenement.target_id,
        "incidents_before": active_count,
        "incidents_after": active_count - 1,
        "changed_count": sum(n["reduction"] > 0 for n in changements),
        "no_longer_exposed": sum(n["before"] > 0 and n["after"] == 0 for n in changements),
        "nodes": changements,
        "note": "Estimation du modèle : retrait de cet incident et recalcul des autres. "
                "N'inclut ni délai d'intervention, ni trafic, ni missions, ni effet réel garanti.",
    }
