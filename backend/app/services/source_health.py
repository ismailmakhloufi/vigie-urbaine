"""Fraîcheur des données d'entrée, sans confondre silence et panne d'agence."""

from datetime import datetime, timezone

from app.db.mongo_client import mongo_client
from app.services import sources

WEATHER_MAX_AGE_SECONDS = 240  # lecture prévue toutes les 75 s (4 zones)
QUIET_SECONDS = 1800  # les événements simulés ne sont pas périodiques par agence


def ensure_indexes():
    db = mongo_client._db
    db.sensor_readings.create_index([("sensor_id", 1), ("timestamp", -1)])
    db.events.create_index([("timestamp", -1)])
    db.calls.create_index([("created_at", -1)])
    db.vehicles.create_index([("agency_received_at", -1)])


def _as_datetime(value):
    if isinstance(value, str):
        try:
            value = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return None
    if not isinstance(value, datetime):
        return None
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value


def _latest(collection, query, field):
    return mongo_client._db[collection].find_one(query, sort=[(field, -1)])


def _channel(key, label, origin, doc, field, now, stream, periodic=False, simulated=True):
    received = _as_datetime(doc.get(field)) if doc else None
    age = max(0, int((now - received).total_seconds())) if received else None
    if simulated and stream["paused"]:
        status = "PAUSED"
    elif simulated and not stream["online"]:
        status = "STREAM_OFFLINE"
    elif age is None:
        status = "NO_DATA"
    elif age > (WEATHER_MAX_AGE_SECONDS if periodic else QUIET_SECONDS):
        status = "LATE" if periodic else "QUIET"
    else:
        status = "RECENT"
    return {"id": key, "label": label, "origin": origin, "status": status,
            "last_received_at": received.isoformat() if received else None,
            "age_seconds": age, "periodic": periodic}


def overview(now=None):
    """Lecture seule : horodatage de réception, jamais preuve de santé du fournisseur."""
    now = now or datetime.now(timezone.utc)
    stream = sources.stream_status()
    channels = [
        _channel("cacu", "CACU · appels", "simulé / appels reçus",
                 _latest("calls", {}, "created_at"), "created_at", now, stream),
        _channel("voirie", "Voirie · incidents", "agence simulée",
                 _latest("events", {"description": {"$regex": "^Flux agence :"}}, "timestamp"),
                 "timestamp", now, stream),
        _channel("siem", "SIEM / EDR", "virtual-siem",
                 _latest("events", {"payload.source": "virtual-siem"}, "timestamp"),
                 "timestamp", now, stream),
        _channel("scada", "SCADA", "virtual-scada",
                 _latest("events", {"payload.source": "virtual-scada"}, "timestamp"),
                 "timestamp", now, stream),
    ]
    for sensor in sources.SENSORS:
        channels.append(_channel(
            sensor["sensor_id"], f"Open-Meteo · {sensor['zone_name']}", "observation météo",
            _latest("sensor_readings", {"sensor_id": sensor["sensor_id"]}, "timestamp"),
            "timestamp", now, stream, periodic=True,
        ))
    channels.append(_channel(
        "fleet", "Flotte · retours d'agence", "mises à jour externes",
        _latest("vehicles", {"agency_received_at": {"$exists": True}}, "agency_received_at"),
        "agency_received_at", now, stream, simulated=False,
    ))
    return {"checked_at": now.isoformat(), "stream": stream, "channels": channels}
