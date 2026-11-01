"""
Urban Butterfly - Orchestrateur de demonstration

Joue tout seul le scenario de soutenance, comme si les agences reelles
poussaient leurs faits :
    appel -> dispatch auto -> course -> incident soudain -> corridor
    -> resolution. L'operateur n'a plus qu'a commenter a l'oral.

POST /integration/demo {"action": "start"|"stop"}
"""

import json
import threading
import time
from urllib import request as urlreq

API = "http://127.0.0.1:8000"

_thread: threading.Thread | None = None
_stop = threading.Event()
_lock = threading.Lock()


def _push(method: str, path: str, payload: dict | None = None) -> dict:
    """Appel HTTP d'un bout a l'autre du systeme (auto-consommation)."""
    data = json.dumps(payload).encode("utf-8") if payload is not None else None
    req = urlreq.Request(
        f"{API}{path}",
        data=data,
        method=method,
        headers={"Content-Type": "application/json"} if data else {},
    )
    with urlreq.urlopen(req, timeout=60) as resp:
        body = resp.read().decode("utf-8")
        return json.loads(body) if body else {}


def _call(path: str, payload: dict | None = None) -> dict:
    method = "POST" if payload is not None else "GET"
    try:
        return _push(method, path, payload)
    except Exception as exc:
        print(f"[demo] {method} {path} ratee : {exc}")
        return {}


def _script():
    _stop.clear()
    try:
        # == acte 1 : appel entrant, dispatch automatique
        _call("/integration/calls", {
            "kind": "MEDICAL", "destination_id": "H3", "note": "Accident grave — Ariana",
        })
        if _wait(16):
            return

        # == acte 2 : une route saute en pleine course
        created = _call("/events", {
            "type": "ROAD_BLOCKED", "severity": "CRITICAL",
            "target_id": "R11", "description": "Effondrement de pont",
        })
        event_id = created.get("id")
        if _wait(20):
            return

        # == acte 3 : corridor prioritaire sur la mission en course
        missions = _call("/missions?limit=10")
        active = [
            m for m in missions
            if isinstance(m, dict) and m.get("status") in ("EN_ROUTE", "DIVERTED")
        ]
        if active:
            _call(f"/missions/{active[0]['mission_id']}/corridor", {"minutes": 2})
        if _wait(16):
            return

        # == acte 4 : deuxieme appel (logistique) pendant la course
        _call("/integration/calls", {
            "kind": "SUPPLY", "destination_id": "PH8", "note": "Réassort sérum",
        })
        if _wait(14):
            return

        # == acte 5 : la ville reprend le dessus (POST corps vide)
        if event_id:
            _call(f"/events/{event_id}/resolve", {})
    finally:
        _stop.set()
        print("[demo] scenario termine")


def _wait(seconds: int) -> bool:
    return _stop.wait(seconds)


def start_demo() -> dict:
    global _thread
    with _lock:
        if _thread and _thread.is_alive():
            return {"status": "already_running"}
        _thread = threading.Thread(target=_script, daemon=True, name="ub-demo")
        _thread.start()
        return {"status": "started"}


def stop_demo() -> dict:
    if _thread and _thread.is_alive():
        _stop.set()
        return {"status": "stopping"}
    return {"status": "not_running"}


def demo_status() -> dict:
    return {"running": bool(_thread and _thread.is_alive())}
