"""
Vigie Urbaine - Simulateur de sources (le monde physique virtualise)

UN SEUL daemon fait vivre tout le flux de la ville, comme si des tiers
poussaient leurs faits vers le systeme :

    - CACU (15/191)          : appels d'urgence -> dispatch automatique ;
    - voirie / gendarmerie   : ROAD_BLOCKED (accidents, effondrements...) ;
    - capteurs meteo REELS   : Open-Meteo sur les 4 zones, seuils 25/40 mm
                               + vent, auto-declenchement HEAVY_RAIN avec
                               cooldown, lectures stockees (sensor_readings) ;
    - SIEM/EDR virtualise    : CYBER_ATTACK au format SIEM (src_ip, outil) ;
    - SCADA virtualise       : POWER_FAILURE probabiliste.

Les incidents enrichis se resorbent d'eux-memes (auto-resolution) : la
ville vit, se blesse et se repare seule. L'operateur supervise et decide
(corridor, imposer un itineraire, radio, resoudre). Rien d'autre.

GET  /integration/stream -> statut du flux + statistiques
POST /integration/stream {"action": "start"|"stop"}
"""

import random
import threading
import time
import json
import logging
import urllib.request
from datetime import datetime, timedelta, timezone

from app.db.mongo_client import mongo_client
from app.db.neo4j_client import neo4j_client
from app.services import dispatcher, simulation_activity

logger = logging.getLogger(__name__)

# ----- rythmes du monde -----
CALL_EVERY = (35, 90)        # intervalle entre appels d'urgence (s)
INCIDENT_EVERY = (110, 240)  # intervalle entre incidents (s)
WEATHER_EVERY = 75           # lecture des capteurs meteo (s)
RESOLVE_AFTER = (150, 360)   # duree de vie d'un incident (s)

# ----- seuils meteo (cahier des charges, section 9) -----
RAIN_CRITICAL_MM = 40.0
RAIN_HIGH_MM = 25.0
WIND_CRITICAL_KMH = 60.0
WIND_HIGH_KMH = 40.0
COOLDOWN_METEO = timedelta(minutes=90)

# Les zones du graphe avec leurs coordonnees reelles
SENSORS = [
    {"sensor_id": "weather_01", "zone": "Z1", "zone_name": "Tunis Centre", "lat": 36.80, "lon": 10.18},
    {"sensor_id": "weather_02", "zone": "Z2", "zone_name": "La Marsa", "lat": 36.87, "lon": 10.30},
    {"sensor_id": "weather_03", "zone": "Z3", "zone_name": "L ARIANA", "lat": 36.86, "lon": 10.20},
    {"sensor_id": "weather_04", "zone": "Z4", "zone_name": "Ben Arous", "lat": 36.75, "lon": 10.23},
]

# ----- alertes cyber SIEM/EDR -----
CYBER_TYPES = ["RANSOMWARE", "DDOS", "DATA_EXFILTRATION", "PHISHING", "BRUTE_FORCE"]
CYBER_TOOLS = ["nids", "edr-agent", "wazuh", "suricata"]
CYBER_SEVERITIES = ["LOW", "MEDIUM", "HIGH", "CRITICAL"]
CYBER_WEIGHTS = [4, 3, 2, 1]  # CRITICAL rare (1 tirage sur 10)

TECH_TARGETS = [f"P{i}" for i in range(1, 6)] + [f"T{i}" for i in range(1, 11)]


_thread: threading.Thread | None = None
_stop = threading.Event()
_lock = threading.Lock()
_control_lock = threading.Lock()
_stats = {"calls": 0, "incidents": 0, "resolved": 0, "alertes_meteo": 0, "rejets": 0, "doublons": 0}
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
        simulation_activity.record("CALL", f"Appel {call['kind']} vers {call['destination_id']} · {call['status']}",
                                   "CACU simulé", call["call_id"])
        if call.get("mission_id"):
            simulation_activity.record("DISPATCH", f"Mission {call['mission_id']} confiée à {call.get('assigned_vehicle')}",
                                       "dispatcher", call["mission_id"])
        if call.get("status") in ("PENDING", "ROUTE_UNAVAILABLE"):
            print(
                f"[sources] appel #{_stats['calls']} : {call['call_id']} "
                f"({call['kind']}/{call['destination_id']}) -> {call['status']}"
            )
        else:
            print(
                f"[sources] appel #{_stats['calls']} : {call['call_id']} "
                f"({call['kind']}/{call['destination_id']}) -> {call['assigned_vehicle']}"
            )
    except RuntimeError:
        _stats["rejets"] += 1
    except Exception as exc:
        print(f"[sources] appel rate : {exc}")


# ================================== voirie ==================================

def _pick_road() -> str | None:
    rows = neo4j_client.query(
        "MATCH (r:Road {status: 'CLEAR'}) RETURN r.id AS id ORDER BY rand() LIMIT 5"
    )
    return random.choice(rows)["id"] if rows else None


def _push_road_incident():
    rid = _pick_road()
    if not rid:
        return
    severity = "CRITICAL" if random.random() < 0.35 else "HIGH"
    reason = random.choice([
        "accident de la route", "effondrement de pilier", "manifestation",
        "fuite de gaz", "eau sur la chaussee", "camion renverse",
    ])
    event_id = _create_event(
        "ROAD_BLOCKED", severity, rid, f"Flux agence : {reason}"
    )
    _register(event_id)


# ================================== meteo ===================================

def fetch_weather(lat: float, lon: float) -> dict:
    url = (
        "https://api.open-meteo.com/v1/forecast"
        f"?latitude={lat}&longitude={lon}"
        "&current=temperature_2m,relative_humidity_2m,precipitation,wind_speed_10m"
        "&timezone=Africa/Tunis"
    )
    with urllib.request.urlopen(url, timeout=10) as resp:
        payload = json.loads(resp.read().decode("utf-8"))
    return payload.get("current", {})


def weather_risk(current: dict) -> tuple[str, str | None]:
    """Traduit une mesure meteo reelle en (severity, event_type | None)."""
    rain = current.get("precipitation") or 0.0
    wind = current.get("wind_speed_10m") or 0.0
    if rain >= RAIN_CRITICAL_MM or wind >= WIND_CRITICAL_KMH:
        return "CRITICAL", "HEAVY_RAIN"
    if rain >= RAIN_HIGH_MM or wind >= WIND_HIGH_KMH:
        return "HIGH", "HEAVY_RAIN"
    return "LOW", None


def _in_cooldown(zone_id: str) -> bool:
    since = datetime.now(timezone.utc) - COOLDOWN_METEO
    return mongo_client._db.events.count_documents(
        {"type": "HEAVY_RAIN", "target_id": zone_id, "timestamp": {"$gte": since}}
    ) > 0


def _weather_tick():
    """Lecture reelle des 4 capteurs ; HEAVY_RAIN automatique aux seuils."""
    for sensor in SENSORS:
        if _stop.is_set():
            return
        try:
            current = fetch_weather(sensor["lat"], sensor["lon"])
            if _stop.is_set():
                return
            if not isinstance(current, dict) or not any(
                current.get(field) is not None for field in
                ("temperature_2m", "precipitation", "wind_speed_10m", "relative_humidity_2m")
            ):
                raise ValueError("mesure météo absente")
        except Exception as exc:
            print(f"[sources] capteur {sensor['sensor_id']} : echec meteo ({exc})")
            simulation_activity.record("WEATHER_ERROR", f"Mesure indisponible : {sensor['zone_name']}",
                                       "Open-Meteo", sensor["sensor_id"])
            continue

        reading = {
            "sensor_id": sensor["sensor_id"],
            "zone": sensor["zone"],
            "zone_name": sensor["zone_name"],
            "temperature_c": current.get("temperature_2m"),
            "rainfall_mm": current.get("precipitation"),
            "humidity_pct": current.get("relative_humidity_2m"),
            "wind_kmh": current.get("wind_speed_10m"),
            "source": "open-meteo",
            "timestamp": _utc_now(),
        }
        mongo_client._db.sensor_readings.insert_one(reading)
        simulation_activity.record("WEATHER", f"Mesure {sensor['zone_name']} · pluie {reading['rainfall_mm']} mm, vent {reading['wind_kmh']} km/h",
                                   "Open-Meteo (observation)", sensor["sensor_id"])

        severity, event_type = weather_risk(current)
        if event_type and not _in_cooldown(sensor["zone"]):
            event_id = _create_event(
                event_type, severity, sensor["zone"],
                f"Meteo reelle zone {sensor['zone_name']} : "
                f"{reading.get('rainfall_mm')} mm/h, vent {reading.get('wind_kmh')} km/h",
            )
            _register(event_id)
            _stats["alertes_meteo"] += 1
            print(
                f"[sources] meteo REELLE : HEAVY_RAIN {severity} sur "
                f"{sensor['zone_name']} ({reading.get('rainfall_mm')} mm/h)"
            )


# ================================ cyber / tech ===============================

def _push_cyber():
    target = random.choice(
        [f"P{i}" for i in range(1, 6)] + [f"H{i}" for i in range(1, 6)]
        + [f"T{i}" for i in range(1, 11)] + ["W1", "W2", "W3"]
    )
    severity = random.choices(CYBER_SEVERITIES, weights=CYBER_WEIGHTS)[0]
    attack = random.choice(CYBER_TYPES)
    event_id = _create_event(
        "CYBER_ATTACK", severity, target,
        f"Alerte SIEM : {attack} contre {target}",
        payload={
            "source": "virtual-siem",
            "tool": random.choice(CYBER_TOOLS),
            "src_ip": f"10.{random.randint(0, 255)}.{random.randint(0, 255)}.{random.randint(1, 254)}",
        },
    )
    _register(event_id)


def _push_tech():
    target = random.choice(TECH_TARGETS)
    severity = random.choices(["HIGH", "CRITICAL"], weights=[6, 4])[0]
    event_id = _create_event(
        "POWER_FAILURE", severity, target,
        f"Défaillance technique simulée sur {target}",
        payload={"source": "virtual-scada", "component": "transformer"},
    )
    _register(event_id)


# ============================== noyau du flux ===============================

def _create_event(
    etype: str, severity: str, target_id: str, description: str,
    payload: dict | None = None,
) -> str | None:
    from app.models.event import EventCreate
    from app.routes.events import create_event

    # un seul incident actif par (type, cible) : pas de doublon de flux
    deja = mongo_client._db.events.count_documents(
        {"type": etype, "target_id": target_id, "status": {"$ne": "RESOLVED"}}
    )
    if deja:
        _stats["doublons"] += 1
        print(f"[sources] doublon refuse ({etype}/{target_id})")
        return None

    deadline = datetime.now(timezone.utc) + timedelta(seconds=random.uniform(*RESOLVE_AFTER))
    try:
        result = create_event(EventCreate(
            type=etype,
            severity=severity,
            target_id=target_id,
            description=description,
            payload=payload or {"source": "flux-automatique"},
            auto_resolve_at=deadline,
        ))
        return result["id"]
    except Exception as exc:
        print(f"[sources] incident rate ({etype}/{target_id}) : {exc}")
        return None


def _register(event_id: str | None):
    """Enregistre un incident pour sa resolution automatique."""
    if not event_id:
        return
    _stats["incidents"] += 1
    event = mongo_client.get_event(event_id)
    if event:
        simulation_activity.record("INCIDENT", f"{event['type']} · {event['target_id']} · {event['severity']}",
                                   str((event.get("payload") or {}).get("source") or "simulation"), event_id)
    if event and event.get("auto_resolve_at"):
        with _lock:
            _pending.append((event_id, event["auto_resolve_at"].timestamp()))
    print(f"[sources] incident #{_stats['incidents']} pousse ({event_id[:8]})")


def _push_incident():
    """Roulette des incidents NON meteo : voirie domine, SIEM/SCADA ensuite."""
    roulette = random.random()
    if roulette < 0.65:
        _push_road_incident()
    elif roulette < 0.85:
        _push_cyber()
    else:
        _push_tech()


def _resolve_expired():
    from app.routes.events import resolve_event

    with _lock:
        now = _now()
        dus = [(eid, exp) for eid, exp in _pending if exp <= now]
    for eid, _ in dus:
        try:
            resolve_event(eid)
            _stats["resolved"] += 1
            simulation_activity.record("RESOLVED", f"Incident {eid[:8]} résolu automatiquement",
                                       "simulateur", eid)
            print(f"[sources] incident #{eid[:8]} resolu naturellement")
        except Exception as exc:
            print(f"[sources] resolution ratee ({eid[:8]}) : {exc}")
            continue  # même échéance, prochain tour : réessai
        with _lock:
            _pending[:] = [(ident, exp) for ident, exp in _pending if ident != eid]


def _restore_pending():
    """Mongo fait autorité après redémarrage, même si _register n'a pas tourné."""
    mongo_client.restore_legacy_auto_resolve(RESOLVE_AFTER[1])
    rows = mongo_client.auto_resolve_events()
    restored = []
    for row in rows:
        deadline = row["auto_resolve_at"]
        if deadline.tzinfo is None:
            deadline = deadline.replace(tzinfo=timezone.utc)
        restored.append((str(row["_id"]), deadline.timestamp()))
    with _lock:
        _pending[:] = restored


def _resume_clock():
    """Le temps simulé ne s'écoule pas entre deux actions manuelles de démarrage."""
    control = mongo_client._db.simulation_control.find_one({"_id": "clock"})
    stopped = control.get("stopped_at") if control else None
    if stopped:
        if stopped.tzinfo is None:
            stopped = stopped.replace(tzinfo=timezone.utc)
        delta = datetime.now(timezone.utc) - stopped
        for event in mongo_client._db.events.find({"status": "ACTIVE", "auto_resolve_at": {"$exists": True}}):
            mongo_client._db.events.update_one({"_id": event["_id"]},
                {"$set": {"auto_resolve_at": event["auto_resolve_at"] + delta}})
        for mission in mongo_client._db.missions.find({"status": {"$in": ["EN_ROUTE", "DIVERTED"]}}):
            fields = {"departure_at": mission["departure_at"] + delta}
            if mission.get("corridor_until"):
                fields["corridor_until"] = (datetime.fromisoformat(mission["corridor_until"]) + delta).isoformat()
            mongo_client._db.missions.update_one({"_id": mission["_id"]},
                {"$set": fields})
        for vehicle in mongo_client._db.vehicles.find({"status": "RETURNING"}):
            fields = {}
            for key in ("return_started", "return_until"):
                if vehicle.get(key):
                    fields[key] = (datetime.fromisoformat(vehicle[key]) + delta).isoformat()
            if fields:
                mongo_client._db.vehicles.update_one({"_id": vehicle["_id"]}, {"$set": fields})
    mongo_client._db.simulation_control.update_one({"_id": "clock"},
        {"$set": {"stopped_at": None}}, upsert=True)


def _loop():
    print("[sources] flux automatique demarre (appels + voirie + SIEM + SCADA)")
    clock = 0.0                       # temps du flux (gele pendant la pause)
    next_call = random.uniform(*CALL_EVERY)
    next_incident = random.uniform(*INCIDENT_EVERY)
    next_weather = WEATHER_EVERY

    while not _stop.is_set():
        _stop.wait(0.5)
        if _stop.is_set():
            continue
        clock += 0.5

        if clock >= next_call:
            _push_call()
            next_call = clock + random.uniform(*CALL_EVERY)

        if not _stop.is_set() and clock >= next_incident:
            _push_incident()
            next_incident = clock + random.uniform(*INCIDENT_EVERY)

        if not _stop.is_set() and clock >= next_weather:
            try:
                _weather_tick()
            except Exception as exc:
                print(f"[sources] tour meteo ratee : {exc}")
            next_weather = clock + WEATHER_EVERY

        if not _stop.is_set():
            _resolve_expired()

    print("[sources] flux automatique arrete")


def start_stream() -> dict:
    global _thread, _started_at
    with _control_lock:
        if _thread and _thread.is_alive():
            if _stop.is_set():
                return {"status": "stopping"}
            return {"status": "already_running"}
        _resume_clock()
        _restore_pending()
        _stop.clear()
        _started_at = _utc_now()
        _thread = threading.Thread(target=_loop, daemon=True, name="ub-sources")
        _thread.start()
        simulation_activity.record("START", "Simulateur démarré par l'opérateur")
        return {"status": "started"}


def stop_stream(reason: str = "Simulateur arrêté par l'opérateur") -> dict:
    with _control_lock:
        was_running = bool(_thread and _thread.is_alive() and not _stop.is_set())
        _stop.set()
        if was_running:
            try:
                mongo_client._db.simulation_control.update_one({"_id": "clock"},
                    {"$set": {"stopped_at": datetime.now(timezone.utc)}}, upsert=True)
            except Exception:
                logger.exception("Horloge de simulation indisponible lors de l'arrêt")
            simulation_activity.record("STOP", reason)
            _thread.join(timeout=12)
        return {"status": "stopping" if _thread and _thread.is_alive() else "stopped"}


def stream_status() -> dict:
    with _lock:
        en_attente = len(_pending)
    return {
        "online": bool(_thread and _thread.is_alive() and not _stop.is_set()),
        "paused": False,
        "running": bool(_thread and _thread.is_alive() and not _stop.is_set()),
        "started_at": _started_at,
        "pending_resolutions": en_attente,
        "stats": dict(_stats),
    }
