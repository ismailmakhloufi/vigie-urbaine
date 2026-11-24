"""Comparaison de résolutions hypothétiques à partir d'un seul état du graphe.

Aucune mutation : les mêmes propagations sont recalculées avec un incident
en moins et un compteur d'incidents simultanés ajusté.
"""

from app.db.mongo_client import mongo_client
from app.services.cascade import compute_impact
from app.services.risk import risk_class, score_node


def _scores(impacts) -> dict:
    nodes = {}
    for impact in impacts:
        for node in impact.impacts:
            if node.id not in nodes or node.score > nodes[node.id].score:
                nodes[node.id] = node
    return nodes


def _rescore(impact, active_count):
    """Réévalue les mêmes liens sans relire Neo4j ni altérer les sources."""
    rescored = []
    for node in impact.impacts:
        score, reasons = score_node(
            kind=node.kind, depth=node.depth,
            criticality=node.criticality,
            backup_power_hours=node.backup_power_hours,
            severity=impact.severity, active_incidents=active_count,
            event_type=impact.event_type,
        )
        rescored.append(node.model_copy(update={
            "score": score, "risk": risk_class(score), "reasons": reasons,
        }))
    return impact.model_copy(update={"impacts": rescored})


def _scenario(event_id, impacts, before, count):
    event = next(impact for impact in impacts if impact.event_id == event_id)
    after = _scores(_rescore(impact, max(0, count - 1))
                    for impact in impacts if impact.event_id != event_id)
    changes = []
    for ident, node in before.items():
        final_score = after[ident].score if ident in after else 0
        changes.append({
            "id": ident, "name": node.name, "kind": node.kind,
            "before": node.score, "after": final_score,
            "reduction": node.score - final_score,
            "risk_before": risk_class(node.score),
            "risk_after": risk_class(final_score) if final_score else None,
        })
    changes.sort(key=lambda n: (-n["reduction"], -n["before"], n["id"]))
    improvements = [node for node in changes if node["reduction"] > 0]
    hospitals = [node for node in improvements if node["kind"] == "Hospital"]
    return {
        "event_id": event_id,
        "event_type": event.event_type,
        "target_id": event.target_id,
        "incidents_before": count,
        "incidents_after": max(0, count - 1),
        "changed_count": len(improvements),
        "no_longer_exposed": sum(n["after"] == 0 for n in improvements),
        "hospital_count": len(hospitals),
        "hospital_points": sum(n["reduction"] for n in hospitals),
        "total_points": sum(n["reduction"] for n in improvements),
        "nodes": changes,
        "note": "Projection du modèle, sans intervention réelle. Les scores ne tiennent "
                "pas compte du trafic, des missions ni du temps de réparation. "
                "Ils peuvent évoluer avec les autres incidents ; aucun résultat n'est garanti.",
    }


def scenarios() -> list[dict]:
    """Un seul lot de lectures Neo4j par incident pour toutes les projections."""
    ids = mongo_client.get_active_events()
    if not ids:
        return []
    count = mongo_client.count_active_events()
    impacts = [compute_impact(eid, active_incidents=count) for eid in ids]
    before = _scores(impacts)
    return [_scenario(eid, impacts, before, count) for eid in ids]


def ranked_scenarios(include_access=True) -> list[dict]:
    ranked = scenarios()
    # Classement analytique : priorité aux hôpitaux, puis au gain global.
    ranked.sort(key=lambda s: (-s["hospital_points"], -s["total_points"], s["event_id"]))
    if include_access:
        from app.services import fleet
        from app.services.routing import compute_route

        vehicles = fleet.available()
        cache = {}
        for item in ranked:
            if not vehicles:
                item["access"] = {"status": "NO_VEHICLE"}
                continue
            best = None
            for vehicle in vehicles:
                base = vehicle.get("base_id")
                if not base:
                    continue
                key = (base, item["target_id"], vehicle.get("type", "NORMAL"))
                if key not in cache:
                    try:
                        route = compute_route(key[0], key[1], profile=key[2])
                        cache[key] = route["estimated_time_min"]
                    except (LookupError, RuntimeError, ValueError):
                        cache[key] = None
                travel = cache[key]
                if travel is not None and (best is None or travel < best["minutes"]):
                    best = {"status": "REACHABLE", "minutes": travel,
                            "base_id": base, "vehicle": vehicle["callsign"]}
            item["access"] = best or {"status": "NO_ROUTE"}
    return ranked
