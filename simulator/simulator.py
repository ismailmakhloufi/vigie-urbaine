"""
URBAN BUTTERFLY - simulateur du monde physique (etape 7 du plan).

Produit le "pouls" de la ville :
  - meteo reelle via Open-Meteo (gratuit, sans cle) -> stockee dans Mongo
    (collection sensor_readings), avec seuils qui auto-declenchent
    HEAVY_RAIN sur une zone (avec anti-repetition = cooldown)
  - alertes cyber style SIEM -> POST /events (CYBER_ATTACK)
  - pannes techniques probabilistes -> POST /events (POWER_FAILURE)

Usage (avec le venv du backend) :
  backend/.venv/Scripts/python simulator/simulator.py weather-once
  backend/.venv/Scripts/python simulator/simulator.py cyber-once
  backend/.venv/Scripts/python simulator/simulator.py tech-once
  backend/.venv/Scripts/python simulator/simulator.py status
  backend/.venv/Scripts/python simulator/simulator.py loop --interval 30
"""

import argparse
import json
import os
import random
import time
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

from pymongo import MongoClient

BACKEND_ENV = Path(__file__).resolve().parent.parent / "backend" / ".env"


def load_env(path: Path) -> dict:
    env = {}
    if path.exists():
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, value = line.split("=", 1)
                env[key] = value
    return env


ENV = load_env(BACKEND_ENV)
MONGO_URI = ENV.get("MONGO_URI", "mongodb://admin:urbanbutterfly@localhost:27017")
MONGO_DB = ENV.get("MONGO_DB", "urban_butterfly")
API = f"http://{ENV.get('API_HOST', '127.0.0.1')}:{ENV.get('API_PORT', '8000')}"

_mongo = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
db = _mongo[MONGO_DB]

# Les deux zones du graphe avec leurs coordonnees
SENSORS = [
    {"sensor_id": "weather_01", "zone": "Z1", "zone_name": "Tunis Centre", "lat": 36.80, "lon": 10.18},
    {"sensor_id": "weather_02", "zone": "Z2", "zone_name": "Tunis Nord", "lat": 36.86, "lon": 10.16},
]

# Seuils meteo -> evenements (section 9 du cahier des charges)
RAIN_CRITICAL_MM = 40.0
RAIN_HIGH_MM = 25.0
WIND_CRITICAL_KMH = 60.0
WIND_HIGH_KMH = 40.0

# Anti-repetition : la meme pluie ne declenche pas un 2e event tout de suite
COOLDOWN = timedelta(minutes=90)

# Alertes cyber generees (format proche SIEM/EDR, section 9)
CYBER_TYPES = ["RANSOMWARE", "DDOS", "DATA_EXFILTRATION", "PHISHING", "BRUTE_FORCE"]
CYBER_TARGETS = ["P1", "P2", "T1", "T2", "H1", "H2", "W1"]
CYBER_SEVERITIES = ["LOW", "MEDIUM", "HIGH", "CRITICAL"]
CYBER_WEIGHTS = [4, 3, 2, 1]

# Probabilites par tick : les incidents doivent rester RARES pour rester credibles
P_CYBER = 0.10
P_TECH = 0.05
TECH_TARGETS = ["P1", "P2", "T1", "T2"]


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


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


def weather_risk(current: dict):
    """Traduit une mesure meteo en (severity, event_type | None)."""
    rain = current.get("precipitation") or 0.0
    wind = current.get("wind_speed_10m") or 0.0
    if rain >= RAIN_CRITICAL_MM or wind >= WIND_CRITICAL_KMH:
        return "CRITICAL", "HEAVY_RAIN"
    if rain >= RAIN_HIGH_MM or wind >= WIND_HIGH_KMH:
        return "HIGH", "HEAVY_RAIN"
    return "LOW", None


def in_cooldown(zone_id: str) -> bool:
    since = now_utc() - COOLDOWN
    count = db.events.count_documents(
        {"type": "HEAVY_RAIN", "target_id": zone_id, "timestamp": {"$gte": since}}
    )
    return count > 0


def post_to_api(path: str, body: dict) -> dict:
    data = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(
        f"{API}{path}", data=data, headers={"Content-Type": "application/json"}, method="POST"
    )
    try:
        with urllib.request.urlopen(req, timeout=8) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except Exception as exc:
        return {"error": f"API indisponible ({exc})"}


def weather_once(publish: bool = True) -> str:
    lines = []
    for sensor in SENSORS:
        try:
            current = fetch_weather(sensor["lat"], sensor["lon"])
        except Exception as exc:
            lines.append(f"[{sensor['sensor_id']}] echec API meteo : {exc}")
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
            "timestamp": now_utc().isoformat(),
        }
        db.sensor_readings.insert_one(reading)
        reading.pop("_id", None)
        lines.append(f"[{sensor['sensor_id']}] {json.dumps(reading, ensure_ascii=False)}")

        if publish:
            severity, event_type = weather_risk(current)
            if event_type and not in_cooldown(sensor["zone"]):
                body = {
                    "type": event_type,
                    "severity": severity,
                    "target_id": sensor["zone"],
                    "description": (
                        f"Meteo reelle zone {sensor['zone_name']}: "
                        f"{reading['rainfall_mm']} mm/h, vent {reading['wind_kmh']} km/h"
                    ),
                    "payload": {"source": "virtual-weather-sensor", "sensor_id": sensor["sensor_id"]},
                }
                result = post_to_api("/events", body)
                lines.append(f"    -> AUTO-EVENEMENT {severity} : {json.dumps(result, ensure_ascii=False)}")
    return "\n".join(lines)


def cyber_once(force: bool = False) -> str:
    if not force and random.random() >= P_CYBER:
        return "[cyber] Pas d'alerte ce tick."
    target = random.choice(CYBER_TARGETS)
    severity = random.choices(CYBER_SEVERITIES, weights=CYBER_WEIGHTS)[0]
    attack = random.choice(CYBER_TYPES)
    body = {
        "type": "CYBER_ATTACK",
        "severity": severity,
        "target_id": target,
        "description": f"Alerte SIEM : {attack} contre {target}",
        "payload": {
            "source": "virtual-siem",
            "tool": random.choice(["nids", "edr-agent", "wazuh", "suricata"]),
            "src_ip": f"10.{random.randint(0,255)}.{random.randint(0,255)}.{random.randint(1,254)}",
        },
    }
    return "[cyber] " + json.dumps(post_to_api("/events", body), ensure_ascii=False)


def tech_once(force: bool = False) -> str:
    if not force and random.random() >= P_TECH:
        return "[tech] Pas de defaillance ce tick."
    target = random.choice(TECH_TARGETS)
    severity = random.choices(["HIGH", "CRITICAL"], weights=[6, 4])[0]
    body = {
        "type": "POWER_FAILURE",
        "severity": severity,
        "target_id": target,
        "description": f"Defaillance technique simulee sur {target}",
        "payload": {"source": "virtual-scada", "component": "transformer"},
    }
    return "[tech] " + json.dumps(post_to_api("/events", body), ensure_ascii=False)


def loop(interval: int) -> None:
    print(f"Mode boucle : 1 tick / {interval}s (Ctrl+C pour arreter)")
    tick = 0
    try:
        while True:
            tick += 1
            print(f"\n===== TICK {tick} ({now_utc().isoformat()}) =====")
            print(weather_once())
            print(cyber_once(force=args.force))
            print(tech_once(force=args.force))
            time.sleep(interval)
    except KeyboardInterrupt:
        print("\nSimulateur arrete.")


def status() -> str:
    active = db.events.count_documents({"status": {"$ne": "RESOLVED"}})
    readings = list(db.sensor_readings.find({}, {"_id": 0}).sort("timestamp", -1).limit(4))
    out = [f"incidents actifs : {active}", "dernieres lectures gun capteurs :"]
    for reading in readings:
        out.append(json.dumps(reading, ensure_ascii=False))
    return "\n".join(out)


def main():
    parser = argparse.ArgumentParser(description="Urban Butterfly - monde virtuel")
    parser.add_argument("mode", choices=["weather-once", "cyber-once", "tech-once", "loop", "status"])
    parser.add_argument("--interval", type=int, default=30)
    parser.add_argument("--force", action="store_true", help="declenche un incident sans tirage probabiliste")
    args = parser.parse_args()

    if args.mode == "weather-once":
        print(weather_once())
    elif args.mode == "cyber-once":
        print(cyber_once(force=args.force))
    elif args.mode == "tech-once":
        print(tech_once(force=args.force))
    elif args.mode == "loop":
        loop(args.interval)
    else:
        print(status())


if __name__ == "__main__":
    main()
