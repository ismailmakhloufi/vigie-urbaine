"""
Urban Butterfly - Simulateur de sources

En production, ces faits arrivent POUSSÉS par des tiers :
    - le CACU (15/191) envoie les appels d'urgence ;
    - la surveillance (capteurs, ANR, gendarmerie) signale les incidents.

Ici un daemon simule ces sources : il tourne avec le serveur, pousse sur
les memes services que des agences reelles (dispatcher, events) et
laisse le systeme se demener seul. L'operateur supervise et decide :
corridor, imposer un itineraire, radio, resoudre. Rien d'autre.

GET  /integration/stream -> statut du flux
POST /integration/stream {"action": "pause"|"resume"}   (resecours manuel)
"""

import random
import threading
import time
from datetime import datetime, timezone

from app.db.neo4j_client import neo4j_client
from app.services import dispatcher

CALL_EVERY = (35, 90)        # intervalle entre appels d'urgence (s)
INCIDENT_EVERY = (110, 240)  # intervalle entre incidents (s)
RESOLVE_AFTER = (150, 360)   # duree de vie d'un incident (s)

_thread: threading.Thread | None = None
_stop = threading.Event()
_pause = threading.Event()
_lock = threading.Lock()
_stats = {"calls": 0, "incidents": 0, "resolved": 0, "rejets": 0}
_pending: list[tuple[str, float]] = []  # (event_id, expires_at)
_started_at: str | None = None


def _now() -> float:
    return time.time()


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _push_call():
    try:
        call = dispatcher.random_call()
        _stats["calls"] += 1
        print(
            f"[sources] appel #{_stats['calls']} : {call['call_id']} "
            f"({call['kind']}/{call['destination_id']}) -> {call['assigned_vehicle']}"
        )
    except RuntimeError:
        _stats["rejets"] += 1
    except Exception as exc:
        print(f"[sources] appel rate : {exc}")


def _pick_road() -> str | None:
    rows = neo4j_client.query(
        "MATCH (r:Road {status: 'CLEAR'}) RETURN r.id AS id ORDER BY rand() LIMIT 5"
    )
    return random.choice(rows)["id"] if rows else None


def _pick_zone() -> str | None:
    rows = neo4j_client.query(
        "MATCH (z:Zone) RETURN z.id AS id ORDER BY rand() LIMIT 3"
    )
    return random.choice(rows)["id"] if rows else None


def _pick_infra(kinds: tuple[str, ...]) -> str | None:
    rows = neo4j_client.query(
        "MATCH (n:Infrastructure) WHERE n.kind IN $kinds RETURN n.id AS id ORDER BY rand() LIMIT 3",
        {"kinds": list(kinds)},
    )
    return random.choice(rows)["id"] if rows else None


def _create_event(etype: str, severity: str, target_id: str, description: str) -> str | None:
    from app.models.event import EventCreate
    from app.routes.events import create_event

    try:
        result = create_event(EventCreate(
            type=etype,
            severity=severity,
            target_id=target_id,
            description=description,
            payload={"source": "flux-automatique"},
        ))
        return result["id"]
    except Exception as exc:
        print(f"[sources] incident rate ({etype}/{target_id}) : {exc}")
        return None


def _push_incident():
    roulette = random.random()
    if roulette < 0.70:
        rid = _pick_road()
        if not rid:
            return
        severity = "CRITICAL" if random.random() < 0.35 else "HIGH"
        reason = random.choice([
            "accident de la route", "effondrement de pilier", "manifestation",
            "fuite de gaz", "eau sur la chaussee", "camion renverse",
        ])
        event_id = _create_event("ROAD_BLOCKED", severity, rid, f"Flux agence : {reason}")
    elif roulette < 0.85:
        zid = _pick_zone()
        if not zid:
            return
        event_id = _create_event("HEAVY_RAIN", "HIGH", zid, "Flux meteo : orage violent sur la zone")
    else:
        tid = _pick_infra(("Hospital", "PowerStation", "TelecomTower", "Warehouse"))
        if not tid:
            return
        event_id = _create_event("CYBER_ATTACK", "HIGH", tid, "Flux ANR : tentative d'intrusion")

    if not event_id:
        return
    _stats["incidents"] += 1
    with _lock:
        _pending.append((event_id, _now() + random.uniform(*RESOLVE_AFTER)))
    print(f"[sources] incident #{_stats['incidents']} pousse ({event_id[:8]})")


def _resolve_expired():
    from app.routes.events import resolve_event

    with _lock:
        now = _now()
        dus = [(eid, exp) for eid, exp in _pending if exp <= now]
        if dus:
            _pending[:] = [(eid, exp) for eid, exp in _pending if exp > now]
    for eid, _ in dus:
        try:
            resolve_event(eid)
            _stats["resolved"] += 1
            print(f"[sources] incident #{eid[:8]} resolu naturellement")
        except Exception as exc:
            print(f"[sources] resolution ratee ({eid[:8]}) : {exc}")


def _loop():
    print("[sources] flux automatique demarre")
    clock = 0.0                      # temps du flux (gele pendant la pause)
    next_call = random.uniform(*CALL_EVERY)
    next_incident = random.uniform(*INCIDENT_EVERY)

    while not _stop.is_set():
        _stop.wait(0.5)
        if _stop.is_set() or _pause.is_set():
            continue  # pause : le temps du flux est gele
        clock += 0.5

        if clock >= next_call:
            _push_call()
            next_call = clock + random.uniform(*CALL_EVERY)

        if clock >= next_incident:
            _push_incident()
            next_incident = clock + random.uniform(*INCIDENT_EVERY)

        _resolve_expired()

    print("[sources] flux automatique arrete")


def start_stream() -> dict:
    global _thread, _started_at
    if _thread and _thread.is_alive():
        return {"status": "already_running"}
    _stop.clear()
    _pause.clear()
    _started_at = _utc_now()
    _thread = threading.Thread(target=_loop, daemon=True, name="ub-sources")
    _thread.start()
    return {"status": "started"}


def stop_stream() -> dict:
    _stop.set()
    return {"status": "stopping"}


def set_paused(paused: bool) -> dict:
    if paused:
        _pause.set()
        return {"status": "paused"}
    _pause.clear()
    return {"status": "resumed"}


def stream_status() -> dict:
    with _lock:
        en_attente = len(_pending)
    return {
        "online": bool(_thread and _thread.is_alive() and not _pause.is_set()),
        "paused": _pause.is_set(),
        "started_at": _started_at,
        "pending_resolutions": en_attente,
        "stats": dict(_stats),
    }
