"""La santé des sources décrit des réceptions, non une disponibilité présumée."""

import unittest
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import patch

import mongomock
from fastapi.testclient import TestClient

from app.db.mongo_client import mongo_client
from app.main import app
from app.services import fleet, source_health, sources


class SourceHealthTests(unittest.TestCase):
    def setUp(self):
        self.db = mongomock.MongoClient().source_test
        self.now = datetime(2026, 11, 15, 12, 0, tzinfo=timezone.utc)
        self.db_patch = patch.object(mongo_client, "_db", self.db)
        self.stream_patch = patch("app.services.source_health.sources.stream_status",
                                  return_value={"online": True, "paused": False})
        self.settings_patch = patch("app.main.get_settings",
                                    return_value=SimpleNamespace(security_mode="demo"))
        self.close_patch = patch("app.main.mongo_client.close")
        self.neo_close_patch = patch("app.main.neo4j_client.close")
        for item in (self.db_patch, self.stream_patch, self.settings_patch,
                     self.close_patch, self.neo_close_patch):
            item.start()
        source_health.ensure_indexes()

    def tearDown(self):
        for item in (self.neo_close_patch, self.close_patch, self.settings_patch,
                     self.stream_patch, self.db_patch):
            item.stop()

    def test_lecture_recente_silence_et_pause_sans_mutation(self):
        self.db.calls.insert_one({"call_id": "A-1", "created_at": (self.now - timedelta(minutes=45)).isoformat()})
        self.db.events.insert_one({"type": "CYBER_ATTACK", "payload": {"source": "virtual-siem"},
                                   "timestamp": self.now - timedelta(minutes=2)})
        self.db.sensor_readings.insert_one({"sensor_id": "weather_01", "timestamp":
                                            (self.now - timedelta(seconds=241)).isoformat()})
        self.db.sensor_readings.insert_one({"sensor_id": "weather_02", "timestamp":
                                            (self.now - timedelta(seconds=60)).isoformat()})
        self.db.vehicles.insert_one({"callsign": "SAMU-9", "registered_at": self.now.isoformat()})
        before = {name: self.db[name].count_documents({}) for name in
                  ("calls", "events", "sensor_readings", "vehicles")}
        rows = {row["id"]: row for row in source_health.overview(self.now)["channels"]}
        self.assertEqual(rows["cacu"]["status"], "QUIET")
        self.assertEqual(rows["siem"]["status"], "RECENT")
        self.assertEqual(rows["weather_01"]["status"], "LATE")
        self.assertEqual(rows["weather_02"]["status"], "RECENT")
        self.assertEqual(rows["weather_03"]["status"], "NO_DATA")
        self.assertEqual(rows["fleet"]["status"], "NO_DATA")
        self.assertEqual(rows["weather_02"]["age_seconds"], 60)
        self.assertEqual(before, {name: self.db[name].count_documents({}) for name in before})
        with patch("app.services.source_health.sources.stream_status",
                   return_value={"online": False, "paused": True}):
            paused = {row["id"]: row for row in source_health.overview(self.now)["channels"]}
        self.assertEqual(paused["weather_02"]["status"], "PAUSED")
        self.assertEqual(paused["fleet"]["status"], "NO_DATA")

    def test_retour_flotte_externe_uniquement_et_endpoint(self):
        self.db.vehicles.insert_one({"callsign": "SAMU-9", "status": "AVAILABLE"})
        with patch("app.services.fleet._base_coords", return_value={}):
            fleet.integrate_fleet_update({"callsign": "SAMU-9", "status": "ON_MISSION"})
        self.assertIsInstance(self.db.vehicles.find_one({"callsign": "SAMU-9"})["agency_received_at"], datetime)
        with TestClient(app) as client:
            response = client.get("/integration/sources")
        self.assertEqual(response.status_code, 200, response.text)
        channels = {row["id"]: row for row in response.json()["channels"]}
        self.assertEqual(channels["fleet"]["origin"], "mises à jour externes")
        self.assertIsNotNone(channels["fleet"]["last_received_at"])

    def test_reception_available_n_efface_pas_une_reservation(self):
        self.db.vehicles.insert_one({"callsign": "SAMU-12", "status": "RESERVED", "reservation": "A-1"})
        with patch("app.services.fleet._base_coords", return_value={}):
            fleet.integrate_fleet_update({"callsign": "SAMU-12", "status": "AVAILABLE"})
        vehicle = self.db.vehicles.find_one({"callsign": "SAMU-12"})
        self.assertEqual(vehicle["status"], "RESERVED")
        self.assertEqual(vehicle["reservation"], "A-1")
        self.assertIsInstance(vehicle["agency_received_at"], datetime)

    def test_reponse_meteo_vide_n_est_pas_une_lecture(self):
        with patch("app.services.sources.fetch_weather", return_value={}), \
                patch.object(sources, "SENSORS", sources.SENSORS[:1]):
            sources._weather_tick()
        self.assertEqual(self.db.sensor_readings.count_documents({}), 0)


if __name__ == "__main__":
    unittest.main()
