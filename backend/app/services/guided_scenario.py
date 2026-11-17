"""Parcours de démonstration piloté par l'opérateur, sans démarrage automatique."""

import threading
from datetime import datetime, timedelta, timezone

from app.db.mongo_client import mongo_client
from app.db.neo4j_client import neo4j_client
from app.models.event import EventCreate
from app.routes.events import create_event
from app.services import dispatcher, fleet, missions, sources
from app.services.routing import compute_route
from app.services.traffic import congestion_map

_lock = threading.Lock()
STEPS = ("rain", "ambulance", "block", "power")


class ScenarioConflict(RuntimeError):
    """Action impossible dans l'état courant, sans effacer les données."""


def status() -> dict:
    doc = mongo_client._db.guided_scenario.find_one({"_id": "main"}) or {}
    return {"step": doc.get("step", 0), "history": doc.get("history", [])}


def _target(kind: str, event_type: str) -> str:
    healthy_status = "CLEAR" if kind == "Road" else "ONLINE"
    rows = neo4j_client.query(
        "MATCH (n:Infrastructure) WHERE n.kind = $kind "
        "AND (n.status = $healthy_status OR n.status IS NULL) "
        "RETURN n.id AS id ORDER BY n.id",
        {"kind": kind, "healthy_status": healthy_status},
    )
    for row in rows:
        if not mongo_client._db.events.count_documents({
            "type": event_type, "target_id": row["id"], "status": {"$ne": "RESOLVED"},
        }):
            return row["id"]
    raise ScenarioConflict(f"Aucune cible {kind} libre pour {event_type}.")


def _incident(event_type: str, target_id: str, description: str) -> dict:
    result = create_event(EventCreate(
        type=event_type, severity="CRITICAL", target_id=target_id,
        description=description, payload={"source": "scénario guidé simulé"},
        auto_resolve_at=datetime.now(timezone.utc) + timedelta(minutes=10),
    ))
    sources._register(result["id"])
    return {"event_id": result["id"], "target_id": target_id,
            "impact_count": result["impact"].total_count}


def _rain() -> dict:
    target = _target("Zone", "HEAVY_RAIN")
    return {"action": "rain", **_incident(
        "HEAVY_RAIN", target,
        "Pluie extrême fictive du scénario guidé (pas une mesure Open-Meteo)",
    )}


def _ambulance() -> dict:
    fleet.ensure_fleet()
    ambulances = fleet.available("AMBULANCE")
    if not ambulances:
        raise ScenarioConflict("Aucune ambulance disponible : réessayez après son retour à la base.")
    hospitals = neo4j_client.query(
        "MATCH (h:Hospital:Infrastructure) RETURN h.id AS id ORDER BY h.id"
    )
    destination = None
    for hospital in hospitals:
        for vehicle in ambulances:
            try:
                route = compute_route(vehicle["base_id"], hospital["id"], "AMBULANCE")
                if len(route["route"]) >= 3:
                    destination = hospital["id"]
                    break
            except (LookupError, RuntimeError):
                continue
        if destination:
            break
    if not destination:
        raise ScenarioConflict("Aucun trajet médical praticable avec plusieurs tronçons.")
    call = dispatcher.create_call("MEDICAL", destination, "Urgence fictive du scénario guidé")
    return {"action": "ambulance", "call_id": call["call_id"],
            "mission_id": call.get("mission_id"), "destination_id": destination,
            "call_status": call["status"]}


def _block(history: list[dict]) -> dict:
    call_id = history[-1]["call_id"]
    call = mongo_client._db.calls.find_one({"call_id": call_id})
    mission_id = call.get("mission_id") if call else None
    doc = mongo_client.get_mission(mission_id) if mission_id else None
    if not doc or doc["status"] not in ("EN_ROUTE", "DIVERTED"):
        raise ScenarioConflict("L'appel est en attente ou l'ambulance n'est plus en route ; aucun blocage n'a été créé.")
    # Avancer la mission avant de choisir : ne jamais bloquer une route déjà franchie.
    doc = missions._tick_mission(doc)
    if doc["status"] not in ("EN_ROUTE", "DIVERTED"):
        raise ScenarioConflict("L'ambulance est déjà arrivée ou immobilisée ; aucun blocage n'a été créé.")
    route = doc["route"]
    old_names = list(doc.get("route_names", []))
    offsets = doc.get("road_offsets") or []
    distance = offsets[-1]["end_km"] if offsets else 0
    traveled = doc.get("progress", 0) * distance
    seg_idx = next((i for i, offset in enumerate(offsets)
                    if traveled <= offset["end_km"]), 0)
    current_road = route[min(seg_idx, len(route) - 1)]
    selected = None
    for road in route[seg_idx + 1:-1]:
        if mongo_client._db.events.count_documents({
            "type": "ROAD_BLOCKED", "target_id": road, "status": {"$ne": "RESOLVED"},
        }):
            continue
        try:
            alternate = compute_route(current_road, doc["destination_id"], doc["profile"],
                                      extra_blocked={road})
            if road not in alternate["route"] and alternate["route"] != route[seg_idx:]:
                selected = road
                break
        except (LookupError, RuntimeError):
            continue
    if not selected:
        raise ScenarioConflict("Aucune route à bloquer avec détour praticable pour cette ambulance.")
    incident = _incident("ROAD_BLOCKED", selected,
                         f"Route bloquée fictive devant {doc.get('vehicle') or 'l’ambulance'}")
    missions._tick_mission(doc)
    updated = mongo_client.get_mission(mission_id) or doc
    return {"action": "block", **incident, "mission_id": mission_id,
            "previous_route": route, "previous_route_names": old_names,
            "new_route": updated["route"], "new_route_names": updated.get("route_names", []),
            "mission_status": updated["status"], "rerouted": updated["route"] != route,
            "congestion": congestion_map()}


def _power() -> dict:
    target = _target("PowerStation", "POWER_FAILURE")
    return {"action": "power", **_incident(
        "POWER_FAILURE", target, "Panne électrique fictive du scénario guidé",
    )}


def run(action: str) -> dict:
    with _lock:
        if not sources.stream_status()["online"]:
            raise ScenarioConflict("Démarrez vous-même le simulateur avant ce parcours.")
        current = status()
        if action == "reset":
            mongo_client._db.guided_scenario.update_one({"_id": "main"},
                {"$set": {"step": 0, "history": []}}, upsert=True)
            return status()
        if current["step"] >= len(STEPS) or action != STEPS[current["step"]]:
            raise ScenarioConflict("Étape indisponible : suivez l'ordre du parcours guidé.")
        result = {"rain": _rain, "ambulance": _ambulance,
                  "block": lambda: _block(current["history"]), "power": _power}[action]()
        mongo_client._db.guided_scenario.update_one({"_id": "main"},
            {"$set": {"step": current["step"] + 1}, "$push": {"history": result}}, upsert=True)
        return status()
