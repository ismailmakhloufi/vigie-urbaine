"""Parcours HTTP complet en environnement isolé : aucun accès aux bases réelles."""

import unittest
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import patch

import mongomock
from fastapi.testclient import TestClient

from app.db.mongo_client import mongo_client
from app.main import app
from app.models.impact import ImpactNode, ImpactSummary
from app.services import dispatcher


ROUTE = {
    "origin_name": "Dépôt W1", "destination_name": "Hôpital H1",
    "route": ["R1"], "route_names": ["Axe R1"], "avoided": [],
    "distance_km": 3.0, "estimated_time_min": 12,
    "path": [36.80, 10.17, 36.81, 10.19],
    "road_offsets": [{"end_km": 3.0}],
}
BASES = {"W1": [36.80, 10.17], "W2": [36.82, 10.22], "W3": [36.84, 10.26]}


class OperationalJourneyTests(unittest.TestCase):
    def setUp(self):
        db = mongomock.MongoClient().urban_butterfly_test
        self.patches = [
            patch.object(mongo_client, "_db", db),
            patch("app.main.get_settings", return_value=SimpleNamespace(security_mode="demo")),
            patch("app.services.dispatcher._coords_of", return_value=[36.81, 10.19]),
            patch("app.services.fleet._base_coords", return_value=BASES),
            patch("app.services.missions.compute_route", return_value=ROUTE),
            patch("app.services.missions._blocked_roads", return_value=set()),
        ]
        self.mocks = [item.start() for item in self.patches]
        self.db = db
        self.client = TestClient(app)
        self.assertEqual(self.client.get("/fleet").status_code, 200)

    def tearDown(self):
        self.client.close()
        for item in reversed(self.patches):
            item.stop()

    def test_appel_mission_arrivee_et_retour_a_base(self):
        response = self.client.post("/integration/calls", json={
            "kind": "MEDICAL", "destination_id": "H1", "note": "Urgence simulée",
        })
        self.assertEqual(response.status_code, 200, response.text)
        call = response.json()
        self.assertEqual(call["status"], "DISPATCHED")
        vehicle = call["assigned_vehicle"]
        self.assertEqual(self.db.vehicles.find_one({"callsign": vehicle})["status"], "ON_MISSION")
        self.assertEqual(self.db.missions.count_documents({"call_id": call["call_id"]}), 1)
        call_notification = self.db.notifications.find_one({"source_key": f"call:{call['call_id']}"})
        self.assertEqual(call_notification["state"], "NEW")

        future = datetime.now(timezone.utc) + timedelta(minutes=10)
        with patch("app.services.missions._now", return_value=future):
            missions = self.client.get("/missions").json()
        mission = next(m for m in missions if m["mission_id"] == call["mission_id"])
        self.assertEqual(mission["status"], "ARRIVED")
        self.assertEqual(self.db.vehicles.find_one({"callsign": vehicle})["status"], "RETURNING")

        with patch("app.services.fleet._now", return_value=future):
            self.client.get("/fleet")
        self.assertEqual(self.db.vehicles.find_one({"callsign": vehicle})["status"], "AVAILABLE")
        self.assertEqual(self.db.notifications.count_documents({"category": "MISSION"}), 1)
        self.assertEqual(self.client.get("/integration/calls").json()[0]["mission_id"], call["mission_id"])

    def test_route_bloquee_puis_ouverte_l_appel_repart_une_seule_fois(self):
        route = self.mocks[4]
        route.side_effect = RuntimeError("route bloquée")
        call = self.client.post("/integration/calls", json={"destination_id": "H1"}).json()
        self.assertEqual(call["status"], "ROUTE_UNAVAILABLE")
        self.assertEqual(self.db.missions.count_documents({}), 0)
        self.assertEqual(self.db.vehicles.count_documents({"status": "RESERVED"}), 0)
        route.side_effect = None

        dispatcher._file_traiter()
        dispatcher._file_traiter()  # le rappel suivant ne doit pas dupliquer la mission
        saved = self.db.calls.find_one({"call_id": call["call_id"]})
        self.assertEqual(saved["status"], "DISPATCHED")
        self.assertEqual(self.db.missions.count_documents({"call_id": call["call_id"]}), 1)

    def test_flotte_saturee_ne_devient_pas_route_inaccessible(self):
        self.db.vehicles.update_many({}, {"$set": {"status": "OUT_OF_SERVICE"}})
        call = self.client.post("/integration/calls", json={"destination_id": "H1"}).json()
        self.assertEqual(call["status"], "PENDING")
        for _ in range(dispatcher.FILE_MAX_TRIES):
            dispatcher._file_traiter()
        saved = self.db.calls.find_one({"call_id": call["call_id"]})
        self.assertEqual(saved["status"], "NO_VEHICLE")
        self.assertEqual(self.db.missions.count_documents({}), 0)

    def test_incident_projection_resolution_et_historique(self):
        graph = {"status": "CLEAR", "last_event": None}

        def query(cypher, params=None):
            params = params or {}
            if "WHERE t.last_event = $event_id" in cypher:
                if graph["last_event"] != params["event_id"]:
                    return []
                graph.update(status=params["previous_status"], last_event=None)
                return [{"id": "R1", "status": graph["status"]}]
            if "t.last_event = $event_id" in cypher:
                graph.update(status=params["status"], last_event=params["event_id"])
                return []
            if "RETURN t.id AS id" in cypher:
                return [{"id": "R1"}]
            if "t.kind AS kind" in cypher:
                return [{"id": "R1", "kind": "Road", "name": "Route R1", "status": graph["status"]}]
            return []  # création du nœud Event

        def impact(event_id):
            return ImpactSummary(event_id=event_id, event_type="ROAD_BLOCKED", severity="HIGH",
                target_id="R1", impacts=[ImpactNode(id="H1", kind="Hospital", name="Hôpital H1",
                    depth=1, score=80, risk="CRITICAL", criticality=5)],
                direct_count=1, total_count=1, max_depth=1)

        payload = {"type": "ROAD_BLOCKED", "severity": "HIGH", "target_id": "R1"}
        with patch("app.db.neo4j_client.neo4j_client.query", side_effect=query), \
                patch("app.routes.whatif.compute_hypothetical", side_effect=lambda *args: impact("hypothese")), \
                patch("app.routes.events.compute_impact", side_effect=impact), \
                patch("app.routes.risk.compute_impact", side_effect=impact), \
                patch("app.services.interventions.compute_impact", side_effect=lambda eid, **kwargs: impact(eid)):
            projection = self.client.post("/whatif", json=payload)
            self.assertEqual(projection.status_code, 200, projection.text)
            self.assertEqual(self.db.events.count_documents({}), 0)
            self.assertEqual(graph["status"], "CLEAR")

            created = self.client.post("/events", json=payload)
            self.assertEqual(created.status_code, 201, created.text)
            event_id = created.json()["id"]
            self.assertEqual(graph["status"], "BLOCKED")
            self.assertEqual(self.db.notifications.find_one({"source_key": f"event:{event_id}"})["state"], "NEW")
            self.assertEqual(self.client.get("/risk").json()["active_incidents"], 1)

            estimated = self.client.get(f"/events/{event_id}/impact")
            self.assertEqual(estimated.status_code, 200, estimated.text)
            self.assertEqual(estimated.json()["impacts"][0]["id"], "H1")
            self.assertEqual(self.db.events.find_one({})["status"], "ACTIVE")
            self.assertEqual(graph["status"], "BLOCKED")
            self.assertEqual(self.db.notifications.count_documents({}), 1)

            predicted = self.client.get(f"/risk/intervention/{event_id}")
            self.assertEqual(predicted.status_code, 200, predicted.text)
            self.assertEqual(predicted.json()["nodes"][0]["after"], 0)
            self.assertEqual(self.db.events.find_one({})["status"], "ACTIVE")

            resolved = self.client.post(f"/events/{event_id}/resolve")
            self.assertEqual(resolved.status_code, 200, resolved.text)
            self.assertEqual(graph["status"], "CLEAR")
            self.assertEqual(self.db.notifications.find_one({"source_key": f"event:{event_id}"})["state"], "RESOLVED")
            self.assertEqual(self.client.get("/risk").json()["active_incidents"], 0)
            history = self.client.get("/risk/evolution").json()
            self.assertEqual(history[0]["event_id"], event_id)
            self.assertEqual(history[0]["top_changes"][0]["after"], 0)


if __name__ == "__main__":
    unittest.main()
