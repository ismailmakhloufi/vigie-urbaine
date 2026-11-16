"""Aucun générateur ne démarre à l'ouverture de l'API ou à la lecture de la console."""

import unittest
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import patch

import mongomock
from fastapi.testclient import TestClient

from app.db.mongo_client import mongo_client
from app.main import app
from app.services import sources, simulation_activity


class ManualSimulationTests(unittest.TestCase):
    def setUp(self):
        self.db = mongomock.MongoClient().fresh_simulation_test
        self.db_patch = patch.object(mongo_client, "_db", self.db)
        self.settings_patch = patch("app.main.get_settings", return_value=SimpleNamespace(security_mode="demo"))
        self.close_patch = patch("app.main.mongo_client.close")
        self.neo_close_patch = patch("app.main.neo4j_client.close")
        for item in (self.db_patch, self.settings_patch, self.close_patch, self.neo_close_patch):
            item.start()

    def tearDown(self):
        for item in (self.neo_close_patch, self.close_patch, self.settings_patch, self.db_patch):
            item.stop()

    def test_demarrage_uniquement_sur_action_et_journal_vide(self):
        status = {"online": False, "paused": False, "running": False, "stats": {}}
        def start():
            status.update(online=True, running=True)
            return {"status": "started"}
        def stop(reason=""):
            status.update(online=False, running=False)
            return {"status": "stopped"}
        with patch("app.services.sources.start_stream", side_effect=start) as launch, \
                patch("app.services.sources.stop_stream", side_effect=stop), \
                patch("app.services.sources.stream_status", side_effect=lambda: dict(status)), \
                patch("app.services.dispatcher.start_queue") as queue, \
                patch("app.services.dispatcher.stop_queue"), \
                patch("app.services.replay.start_recorder") as recorder, \
                patch("app.services.replay.stop_recorder"):
            with TestClient(app) as client:
                self.assertEqual(client.get("/integration/stream").json()["online"], False)
                self.assertEqual(client.get("/integration/activity").json(), [])
                self.assertEqual(self.db.notifications.count_documents({}), 0)
                launch.assert_not_called()
                queue.assert_not_called()
                recorder.assert_not_called()
                self.assertEqual(client.post("/integration/stream", json={"action": "start"}).json()["online"], True)
                launch.assert_called_once()
                queue.assert_called_once()
                recorder.assert_called_once()
                self.assertEqual(client.post("/integration/stream", json={"action": "stop"}).json()["online"], False)

    def test_horloges_gelees_pendant_l_arret_sans_creer_de_notifications(self):
        now = datetime.now(timezone.utc)
        self.db.simulation_control.insert_one({"_id": "clock", "stopped_at": now - timedelta(minutes=5)})
        deadline = now + timedelta(seconds=20)
        departure = now - timedelta(minutes=3)
        self.db.events.insert_one({"status": "ACTIVE", "auto_resolve_at": deadline})
        self.db.missions.insert_one({"status": "EN_ROUTE", "departure_at": departure})
        self.db.vehicles.insert_one({"status": "RETURNING", "return_started": departure.isoformat(),
                                     "return_until": deadline.isoformat()})
        sources._resume_clock()
        shifted = self.db.events.find_one({})["auto_resolve_at"]
        self.assertAlmostEqual((shifted.replace(tzinfo=timezone.utc) - deadline).total_seconds(), 300, delta=2)
        mission = self.db.missions.find_one({})
        self.assertAlmostEqual((mission["departure_at"].replace(tzinfo=timezone.utc) - departure).total_seconds(), 300, delta=2)
        self.assertEqual(self.db.notifications.count_documents({}), 0)

    def test_journal_garde_les_actions_sans_creer_d_alerte(self):
        simulation_activity.ensure_indexes()
        simulation_activity.record("START", "Démarrage volontaire")
        simulation_activity.record("CALL", "Appel simulé", "CACU", "A-1")
        rows = simulation_activity.recent()
        self.assertEqual([row["action"] for row in rows], ["CALL", "START"])
        self.assertEqual(rows[0]["reference"], "A-1")
        previous = simulation_activity.recent(1, datetime.fromisoformat(rows[0]["at"]), rows[0]["id"])
        self.assertEqual(previous[0]["action"], "START")
        self.assertEqual(self.db.notifications.count_documents({}), 0)


if __name__ == "__main__":
    unittest.main()
