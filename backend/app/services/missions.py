"""
Urban Butterfly - Mission service (suivi de vehicules type SAMU)

Cycle de vie :
    POST /missions           -> appel + depart (compute_route + journal)
    GET  /missions           -> tick : avance le vehicule, detecte les
                                blocages, deroute si necessaire

La position du vehicule est simulee : il progresse le long du trajet
(temps ecoule / ETA) comme le ferait une balise GPS.
"""

import math
from datetime import datetime, timedelta, timezone

from app.db.mongo_client import mongo_client
from app.services.routing import _active_dynamic_state, compute_route

# Simulation GPS : 1 minute reelle = 6 minutes de circulation.
# L'ambulance de la demo n'a donc pas besoin de 34 vraies minutes.
SIMULATION_SPEED = 6.0


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _iso(dt: datetime) -> str:
    return dt.isoformat()


def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2) ** 2
    )
    return 6371.0 * 2 * math.asin(math.sqrt(a))


def _position_on_path(path: list[float], fraction: float) -> tuple[list[float], int]:
    """
    Point GPS a une fraction du chemin (path plat [lat,lon,...]).
    Retourne ([lat, lon], index_road_atteint).
    """
    points = [(path[i], path[i + 1]) for i in range(0, len(path) - 1, 2)]
    if not points:
        return [], 0

    cum = [0.0]
    for i in range(1, len(points)):
        cum.append(cum[-1] + _haversine_km(*points[i - 1], *points[i]))
    total = cum[-1]
    if total <= 0:
        return list(points[0]), 0

    target = max(0.0, min(1.0, fraction)) * total
    for i, c in enumerate(cum):
        if c >= target:
            seg_start = points[max(0, i - 1)]
            seg_end = points[i]
            seg_len = cum[i] - cum[i - 1] if i > 0 else 1e-9
            t = 0.0 if seg_len <= 0 else (target - cum[i - 1]) / seg_len
            lat = seg_start[0] + (seg_end[0] - seg_start[0]) * t
            lon = seg_start[1] + (seg_end[1] - seg_start[1]) * t
            return [round(lat, 6), round(lon, 6)], i
    return list(points[-1]), len(points) - 1


def _blocked_roads() -> set[str]:
    blocked, _, _ = _active_dynamic_state()
    return blocked


def _log(doc: dict, code: str, message: str):
    doc.setdefault("timeline", []).append(
        {"code": code, "message": message, "at": _iso(_now())}
    )


def _next_mission_id() -> str:
    return f"M-{mongo_client.sequence('mission', 'missions', 'mission_id'):02d}"


class RouteUnavailable(RuntimeError):
    """Pas d'itinéraire dans l'état courant du réseau."""


def create_mission(origin_id: str, destination_id: str, profile: str, caller_note: str = "", vehicle: str | None = None, call_id: str | None = None) -> dict:
    """L'appel arrive : calcul du trajet optimal a l'instant T + depart."""
    try:
        route = compute_route(origin_id, destination_id, profile)
    except (RuntimeError, LookupError) as exc:
        raise RouteUnavailable(str(exc)) from exc

    doc = {
        "mission_id": _next_mission_id(),
        "origin_id": origin_id,
        "origin_name": route["origin_name"],
        "destination_id": destination_id,
        "destination_name": route["destination_name"],
        "profile": profile,
        "vehicle": vehicle,
        "call_id": call_id,
        "caller_note": caller_note,
        "status": "EN_ROUTE",
        "route": route["route"],
        "route_names": route["route_names"],
        "avoided": route["avoided"],
        "distance_km": route["distance_km"],
        "eta_min": route["estimated_time_min"],
        "path": route.get("path", []),
        "road_offsets": route.get("road_offsets", []),
        "departure_at": _now(),
        "timeline": [],
    }
    label = f"{vehicle or 'Convoi'}"
    _log(doc, "CALL", f"Appel reçu : {route['origin_name']} → {route['destination_name']}")
    _log(
        doc,
        "DEPART",
        f"Départ {label} depuis {route['origin_name']} · arrivée à {route['estimated_time_min']} min · "
        + " › ".join(route["route_names"]),
    )
    mongo_client.insert_mission(doc)
    return doc


def _release_vehicle(doc: dict, status: str = "AVAILABLE"):
    """Boucle fermee : le vehicule redevient disponible au terme de sa mission."""
    if not doc.get("vehicle"):
        return
    from app.services.fleet import release

    release(doc["mission_id"], doc.get("position") or None, status)


def _tick_mission(doc: dict) -> dict:
    """Avance le vehicule, deroute si une route devant lui est bloquee."""
    if doc["status"] not in ("EN_ROUTE", "DIVERTED"):
        return doc

    _maybe_end_corridor(doc)

    now = _now()
    departure = doc["departure_at"]
    if isinstance(departure, datetime) and departure.tzinfo is None:
        departure = departure.replace(tzinfo=timezone.utc)
    elapsed_min = (now - departure).total_seconds() / 60.0 * SIMULATION_SPEED
    fraction = elapsed_min / max(doc["eta_min"], 1)
    route: list[str] = doc["route"]

    if fraction >= 1.0:
        doc["status"] = "ARRIVED"
        doc["progress"] = 1.0
        doc["position"] = doc["path"][-2:] if len(doc["path"]) >= 2 else []
        _log(doc, "ARRIVE", f"✅ Arrivée à {doc['destination_name']}")
        mongo_client.update_mission(doc["mission_id"], {
            "status": "ARRIVED",
            "progress": 1.0,
            "position": doc["position"],
            "timeline": doc["timeline"],
        })
        from app.services import notifications
        notifications.publish_safely(notifications.publish_mission, doc, "ARRIVED")
        # le convoi ne reste pas sur place : il regagne sa base
        _release_vehicle(doc, status="RETURNING")
        return doc

    path = doc.get("path") or []
    offsets = doc.get("road_offsets") or []
    seg_idx = 0
    if len(path) >= 4:
        position, _ = _position_on_path(path, fraction)
        total_km = offsets[-1]["end_km"] if offsets else 0.0
        target_km = max(0.0, min(1.0, fraction)) * total_km
        for i, offset in enumerate(offsets):
            if target_km <= offset["end_km"] or i == len(offsets) - 1:
                seg_idx = i
                break
    else:
        position = []

    roads_ahead = route[seg_idx:]
    blocked = _blocked_roads()
    collision = next((rid for rid in roads_ahead if rid in blocked), None)

    if collision:
        # on tente de repartir d'ou le vehicule se trouve, sinon du prochaine troncon
        current_road = route[min(seg_idx, len(route) - 1)]
        attempt_roads = [current_road]
        nxt = route[min(seg_idx + 1, len(route) - 1)]
        if nxt != current_road:
            attempt_roads.append(nxt)
        new_route = None
        for cand in attempt_roads:
            if cand in blocked:
                continue
            try:
                new_route = compute_route(cand, doc["destination_id"], doc["profile"])
                break
            except (LookupError, RuntimeError):
                continue

        if new_route is None:
            doc["status"] = "BLOCKED"
            _log(
                doc,
                "BLOCKED",
                f"🚫 {collision} bloquée devant le véhicule : AUCUN accès vers "
                f"{doc['destination_name']}",
            )
            mongo_client.update_mission(doc["mission_id"], {
                "status": "BLOCKED",
                "position": position,
                "timeline": doc["timeline"],
            })
            from app.services import notifications
            notifications.publish_safely(notifications.publish_mission, doc, "BLOCKED")
            _release_vehicle(doc)
            return doc

        remaining_min = int(round(elapsed_min + new_route["estimated_time_min"]))
        doc.update({
            "status": "DIVERTED",
            "route": new_route["route"],
            "route_names": new_route["route_names"],
            "avoided": new_route["avoided"],
            "distance_km": new_route["distance_km"],
            "eta_min": remaining_min,
            "path": new_route.get("path", []),
            "road_offsets": new_route.get("road_offsets", []),
            "departure_at": now,
            "position": position,
            "progress": fraction,
        })
        _log(
            doc,
            "REROUTE",
            f"⚠ {collision} bloquée devant le véhicule : déroutement automatique via "
            + " › ".join(new_route["route_names"]),
        )
        mongo_client.update_mission(doc["mission_id"], {
            "status": doc["status"],
            "route": doc["route"],
            "route_names": doc["route_names"],
            "avoided": doc["avoided"],
            "distance_km": doc["distance_km"],
            "eta_min": doc["eta_min"],
            "path": doc["path"],
            "road_offsets": doc["road_offsets"],
            "departure_at": doc["departure_at"],
            "position": position,
            "progress": fraction,
            "timeline": doc["timeline"],
        })
        return doc

    doc["position"] = position
    doc["progress"] = fraction
    return doc


def radio(mission_id: str, author: str, text: str) -> dict | None:
    """Canal radio : le commandement ou le conducteur parlent dans le journal."""
    doc = mongo_client.get_mission(mission_id)
    if not doc:
        return None
    code = "RADIO_CMD" if author == "CMD" else "RADIO_DRV"
    prefix = "📻 Commandement : " if author == "CMD" else "🎙 Conducteur : "
    _log(doc, code, prefix + text)
    mongo_client.update_mission(mission_id, {"timeline": doc["timeline"]})
    return doc


def choose_route(mission_id: str, variant: str) -> dict:
    """Le commandement impose une variante d'itineraire (comparateur)."""
    doc = mongo_client.get_mission(mission_id)
    if not doc:
        raise LookupError(f"mission {mission_id} introuvable")
    if doc["status"] not in ("EN_ROUTE", "DIVERTED"):
        raise RuntimeError(f"mission terminée ({doc['status']}) — changement impossible")

    # reprise depuis le troncon courant vers la destination
    from app.services.routing import compute_route

    cur_road = doc["route"][0]
    new_route = compute_route(cur_road, doc["destination_id"], doc["profile"], mode=variant)
    labels = {"FAST": "🟢 RAPIDE", "SHORT": "🔵 COURT", "SAFE": "🟠 SÛR"}
    now = _now()
    doc.update({
        "route": new_route["route"],
        "route_names": new_route["route_names"],
        "avoided": new_route["avoided"],
        "distance_km": new_route["distance_km"],
        "eta_min": new_route["estimated_time_min"],
        "path": new_route.get("path", []),
        "road_offsets": new_route.get("road_offsets", []),
        "departure_at": now,
        "position": doc.get("position") or [],
        "progress": 0.0,
    })
    _log(
        doc,
        "REROUTE",
        f"🧑‍✈️ Itinéraire {labels.get(variant, variant)} imposé par le commandement : "
        + " › ".join(new_route["route_names"]),
    )
    mongo_client.update_mission(mission_id, {
        "route": doc["route"],
        "route_names": doc["route_names"],
        "avoided": doc["avoided"],
        "distance_km": doc["distance_km"],
        "eta_min": doc["eta_min"],
        "path": doc["path"],
        "road_offsets": doc["road_offsets"],
        "departure_at": doc["departure_at"],
        "timeline": doc["timeline"],
    })
    return doc


def activate_corridor(mission_id: str, minutes: int = 3) -> dict:
    """Gyrophare : perce la congestion sur son itinéraire pour N minutes."""
    doc = mongo_client.get_mission(mission_id)
    if not doc:
        raise LookupError(f"mission {mission_id} introuvable")
    if doc["status"] not in ("EN_ROUTE", "DIVERTED"):
        raise RuntimeError("mission terminée — corridor inutile")

    from app.services.routing import compute_route

    cur_road = doc["route"][0]
    new_route = compute_route(cur_road, doc["destination_id"], doc["profile"], corridor=True)
    now = _now()
    doc.update({
        "route": new_route["route"],
        "route_names": new_route["route_names"],
        "avoided": new_route["avoided"],
        "distance_km": new_route["distance_km"],
        "eta_min": new_route["estimated_time_min"],
        "path": new_route.get("path", []),
        "road_offsets": new_route.get("road_offsets", []),
        "departure_at": now,
        "progress": 0.0,
        "corridor_until": _iso(now + timedelta(minutes=minutes)),
    })
    _log(
        doc,
        "CORRIDOR",
        f"🚨 {doc.get('vehicle') or 'Convoi'} : CORRIDOR PRIORITAIRE activé "
        f"({minutes} min) — le gyrophare perce la congestion via "
        + " › ".join(new_route["route_names"]),
    )
    mongo_client.update_mission(mission_id, {
        "route": doc["route"],
        "route_names": doc["route_names"],
        "avoided": doc["avoided"],
        "distance_km": doc["distance_km"],
        "eta_min": doc["eta_min"],
        "path": doc["path"],
        "road_offsets": doc["road_offsets"],
        "departure_at": doc["departure_at"],
        "corridor_until": doc["corridor_until"],
        "timeline": doc["timeline"],
    })
    return doc


def _maybe_end_corridor(doc: dict):
    until = doc.get("corridor_until")
    if not until or doc["status"] in ("ARRIVED", "BLOCKED", "CANCELLED"):
        return
    if isinstance(until, str):
        try:
            until = datetime.fromisoformat(until)
        except ValueError:
            return
    if until.tzinfo is None:
        until = until.replace(tzinfo=timezone.utc)
    if _now() >= until:
        doc["corridor_until"] = None
        _log(doc, "CORRIDOR", "🚨 Corridor prioritaire terminé — situation rétablie")
        mongo_client.update_mission(doc["mission_id"], {"corridor_until": None, "timeline": doc["timeline"]})


def list_missions(limit: int = 30) -> list[dict]:
    """Tick toutes les missions actives puis renvoie les instantanes."""
    ticked = {doc["mission_id"]: _tick_mission(doc) for doc in mongo_client.active_missions()}
    result = list(ticked.values())

    seen = set(ticked)
    for doc in mongo_client.all_missions(limit):
        if doc["mission_id"] not in seen:
            result.append(doc)
    result.sort(
        key=lambda d: (d.get("departure_at") or datetime.min).replace(tzinfo=None),
        reverse=True,
    )
    return result[:limit]


def snapshot(doc: dict) -> dict:
    """Formate une mission pour l'API (dates en ISO)."""
    out = {k: v for k, v in doc.items() if k != "_id"}
    out["departure_at"] = _iso(out["departure_at"]) if isinstance(out.get("departure_at"), datetime) else out.get("departure_at")
    out["remaining_min"] = max(
        0,
        int(round(doc["eta_min"] * (1 - min(doc.get("progress", 0.0), 1.0)))),
    )
    corridor_until = doc.get("corridor_until")
    active = False
    if corridor_until:
        try:
            if isinstance(corridor_until, str):
                corridor_until = datetime.fromisoformat(corridor_until)
            if corridor_until.tzinfo is None:
                corridor_until = corridor_until.replace(tzinfo=timezone.utc)
            active = _now() < corridor_until
        except ValueError:
            active = False
    out["corridor_active"] = active
    return out


def cancel_mission(mission_id: str) -> dict | None:
    doc = mongo_client.get_mission(mission_id)
    if not doc:
        return None
    doc["status"] = "CANCELLED"
    _log(doc, "CANCEL", "Mission annulée par le commandement")
    mongo_client.update_mission(mission_id, {"status": "CANCELLED", "timeline": doc["timeline"]})
    _release_vehicle(doc)
    return doc
