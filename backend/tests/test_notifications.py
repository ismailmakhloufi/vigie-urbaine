"""Boîte d'alertes persistante, idempotente et distincte des incidents."""

import unittest
from types import SimpleNamespace
from unittest.mock import patch

import mongomock
from fastapi.testclient import TestClient

from app.db.mongo_client import mongo_client
from app.main import app
from app.services import notifications


class NotificationsTests(unittest.TestCase):
    def setUp(self):
        self.db = mongomock.MongoClient().notifications_test
        self.patches = [
            patch.object(mongo_client, "_db", self.db),
            patch("app.main.get_settings", return_value=SimpleNamespace(security_mode="demo")),
        ]
        for item in self.patches:
            item.start()
        notifications.ensure_indexes()
        self.client = TestClient(app)

    def tearDown(self):
        self.client.close()
        for item in reversed(self.patches):
            item.stop()

    def test_evenement_unique_et_acquittement_sans_resolution(self):
        event = {"type": "ROAD_BLOCKED", "severity": "CRITICAL", "target_id": "R1",
                 "payload": {"source": "agence-simulee"}}
        notifications.publish_event("e1", event)
        notifications.publish_event("e1", event)
        self.assertEqual(self.db.notifications.count_documents({}), 1)
        first = self.client.get("/notifications?state=NEW").json()
        self.assertEqual(first["counts"]["NEW"], 1)
        self.assertEqual(first["items"][0]["producer"], "agence-simulee")
        item_id = first["items"][0]["id"]
        response = self.client.post(f"/notifications/{item_id}/acknowledge")
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()["state"], "ACKNOWLEDGED")
        self.assertEqual(response.json()["acknowledged_by"], "operateur-demo")
        notifications.publish_event("e1", event)  # reprise : ne repasse pas à NEW
        self.assertEqual(self.db.notifications.find_one({"source_key": "event:e1"})["state"], "ACKNOWLEDGED")
        self.assertEqual(self.client.get("/notifications?state=NEW").json()["counts"]["NEW"], 0)

        # Une autre session retrouve la même alerte accusée, non résolue.
        other = TestClient(app)
        try:
            saved = other.get("/notifications?state=ACKNOWLEDGED").json()["items"]
        finally:
            other.close()
        self.assertEqual(saved[0]["id"], item_id)
        self.assertEqual(saved[0]["state"], "ACKNOWLEDGED")
        notifications.resolve_event_notification("e1")
        self.assertEqual(self.client.get("/notifications?state=RESOLVED").json()["counts"]["RESOLVED"], 1)
        self.assertIsNone(self.db.events.find_one({"_id": "e1"}))  # aucun incident créé par l'acquittement

    def test_appel_et_mission_gardent_des_origines_distinctes(self):
        notifications.publish_call({"call_id": "A-1", "kind": "MEDICAL", "destination_id": "H1"})
        notifications.publish_mission({"mission_id": "M-1", "destination_id": "H1", "vehicle": "SAMU-9"}, "BLOCKED")
        rows = self.client.get("/notifications?state=NEW").json()["items"]
        self.assertEqual({item["category"] for item in rows}, {"CALL", "MISSION"})
        self.assertEqual({item["location_id"] for item in rows}, {"H1"})
        self.assertEqual(self.client.post("/notifications/invalid/acknowledge").status_code, 404)

    def test_lecture_meteo_reelle_n_est_pas_presentee_comme_capteur_simule(self):
        notifications.publish_event("meteo-1", {
            "type": "HEAVY_RAIN", "severity": "HIGH", "target_id": "Z1",
            "description": "Meteo reelle zone Tunis Centre : 29 mm/h",
            "payload": {"source": "flux-automatique"},
        })
        item = self.client.get("/notifications").json()["items"][0]
        self.assertIn("Open-Meteo", item["producer"])
        self.assertIn("incident simulé", item["detail"])

    def test_observateur_peut_lire_mais_pas_acquitter(self):
        notifications.publish_call({"call_id": "A-2", "kind": "SUPPLY", "destination_id": "W2"})
        item_id = self.client.get("/notifications").json()["items"][0]["id"]
        settings = SimpleNamespace(security_mode="secure", auth_agency_key="x" * 40)
        with patch("app.main.get_settings", return_value=settings), \
                patch("app.main.current_actor", return_value={"name": "observateur", "role": "viewer"}):
            self.assertEqual(self.client.get("/notifications").status_code, 200)
            self.assertEqual(self.client.post(f"/notifications/{item_id}/acknowledge").status_code, 403)

    def test_reprise_des_alertes_ouvertes_sans_rejouer_l_historique_clos(self):
        self.db.events.insert_many([
            {"type": "POWER_FAILURE", "severity": "CRITICAL", "target_id": "P1",
             "status": "ACTIVE", "payload": {"source": "virtual-scada"}},
            {"type": "ROAD_BLOCKED", "severity": "HIGH", "target_id": "R2",
             "status": "RESOLVED"},
        ])
        self.db.calls.insert_many([
            {"call_id": "A-3", "kind": "MEDICAL", "destination_id": "H1", "status": "PENDING"},
            {"call_id": "A-4", "kind": "MEDICAL", "destination_id": "H2", "status": "DISPATCHED"},
        ])
        self.db.missions.insert_many([
            {"mission_id": "M-4", "destination_id": "H1", "status": "BLOCKED"},
            {"mission_id": "M-5", "destination_id": "H2", "status": "ARRIVED"},
        ])
        notifications.reconcile_current()
        notifications.reconcile_current()
        self.assertEqual(self.db.notifications.count_documents({}), 3)
        self.assertEqual(self.client.get("/notifications?state=NEW").json()["counts"]["NEW"], 3)


if __name__ == "__main__":
    unittest.main()
