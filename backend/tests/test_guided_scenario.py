"""Parcours guidé : données isolées, aucun simulateur ni base réelle démarré."""

import unittest
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import patch

import mongomock
from fastapi.testclient import TestClient

from app.db.mongo_client import mongo_client
from app.main import app
from app.services import guided_scenario, missions, routing


ORIGINAL = ["R1", "R2", "R3", "R4"]
DETOUR = ["R1", "R5", "R3", "R4"]


def route(roads):
    return {"origin_name": "Base", "destination_name": "Hôpital", "route": roads,
            "route_names": roads, "avoided": [], "distance_km": 4,
            "estimated_time_min": 20, "path": [36.8, 10.1, 36.81, 10.2],
            "road_offsets": [{"end_km": i + 1} for i in range(len(roads))]}


class GuidedScenarioTests(unittest.TestCase):
    def setUp(self):
        self.db = mongomock.MongoClient().guided_test
        self.online = False
        self.patches = [
            patch.object(mongo_client, "_db", self.db),
            patch("app.main.get_settings", return_value=SimpleNamespace(security_mode="demo")),
            patch("app.services.guided_scenario.sources.stream_status",
                  side_effect=lambda: {"online": self.online}),
            patch("app.services.guided_scenario.neo4j_client.query", side_effect=self.graph),
            patch("app.services.guided_scenario.fleet.ensure_fleet", return_value=2),
            patch("app.services.guided_scenario.fleet.available", return_value=[
                {"callsign": "SAMU-1", "base_id": "W1", "type": "AMBULANCE"}]),
            patch("app.services.guided_scenario.compute_route", side_effect=self.compute),
            patch("app.services.guided_scenario.dispatcher.create_call", side_effect=self.call),
            patch("app.services.guided_scenario.create_event", side_effect=self.event),
            patch("app.services.guided_scenario.sources._register"),
            patch("app.services.guided_scenario.missions._tick_mission", side_effect=self.tick),
            patch("app.services.guided_scenario.congestion_map", return_value={"R5": 2}),
        ]
        self.mocks = [p.start() for p in self.patches]
        self.client = TestClient(app)
        self.event_index = 0
        self.tick_count = 0

    def tearDown(self):
        self.client.close()
        for p in reversed(self.patches):
            p.stop()

    def graph(self, cypher, params=None):
        if "n.kind = $kind" in cypher:
            if params["healthy_status"] != ("CLEAR" if params["kind"] == "Road" else "ONLINE"):
                return []
            return [{"id": "Z1" if params["kind"] == "Zone" else "P1"}]
        if "Hospital:Infrastructure" in cypher:
            return [{"id": "H1"}]
        return []

    def compute(self, origin, destination, profile, extra_blocked=None):
        if extra_blocked:
            return route(DETOUR)
        return route(ORIGINAL)

    def event(self, payload):
        self.event_index += 1
        ident = f"e{self.event_index}"
        self.db.events.insert_one({"type": payload.type, "target_id": payload.target_id,
                                   "status": "ACTIVE", "payload": payload.payload,
                                   "description": payload.description})
        example = SimpleNamespace(id="H1", name="Hôpital H1", risk="HIGH", score=72,
                                  depth=2, reasons=["Dépendance du graphe"],
                                  chain=[{"id": payload.target_id, "name": "Cible"},
                                         {"id": "H1", "name": "Hôpital H1"}])
        return {"id": ident, "target": {"name": "Cible"},
                "impact": SimpleNamespace(total_count=3, max_depth=2, impacts=[example])}

    def call(self, kind, destination, note):
        self.db.calls.insert_one({"call_id": "A-1", "mission_id": "M-1", "status": "DISPATCHED"})
        self.db.missions.insert_one({"mission_id": "M-1", "destination_id": destination,
             "profile": "AMBULANCE", "status": "EN_ROUTE", "route": ORIGINAL.copy(),
             "route_names": ORIGINAL.copy(), "road_offsets": route(ORIGINAL)["road_offsets"],
             "progress": 0, "vehicle": "SAMU-1", "eta_min": 20,
             "origin_name": "Base", "destination_name": "Hôpital"})
        return {"call_id": "A-1", "mission_id": "M-1", "status": "DISPATCHED",
                "assigned_vehicle": "SAMU-1"}

    def tick(self, doc):
        self.tick_count += 1
        if self.tick_count == 2:
            doc["route"] = DETOUR.copy()
            doc["route_names"] = DETOUR.copy()
            doc["status"] = "DIVERTED"
            self.db.missions.update_one({"mission_id": doc["mission_id"]},
                {"$set": {"route": DETOUR.copy(), "route_names": DETOUR.copy(),
                          "status": "DIVERTED"}})
        return doc

    def post(self, action):
        return self.client.post("/integration/scenario", json={"action": action})

    def through_ambulance(self):
        self.online = True
        self.assertEqual(self.post("rain").status_code, 200)
        self.assertEqual(self.post("ambulance").status_code, 200)

    def test_get_is_read_only_and_post_requires_manual_start(self):
        self.assertEqual(self.client.get("/integration/scenario").json(), {"step": 0, "history": []})
        self.assertEqual(self.db.list_collection_names(), [])
        for action in ("rain", "ambulance", "block", "power", "reset"):
            self.assertEqual(self.post(action).status_code, 409)
        self.assertEqual(self.db.events.count_documents({}), 0)

    def test_four_steps_order_duplicates_reroute_and_reset(self):
        self.online = True
        self.assertEqual(self.post("block").status_code, 409)
        self.assertEqual(self.post("rain").json()["step"], 1)
        rain = self.client.get("/integration/scenario").json()["history"][0]
        self.assertEqual(rain["impact_examples"][0]["reasons"], ["Dépendance du graphe"])
        self.assertEqual(rain["impact_examples"][0]["chain"][-1]["id"], "H1")
        self.assertEqual(self.post("rain").status_code, 409)
        self.assertIn("pas une mesure Open-Meteo", self.db.events.find_one({"type": "HEAVY_RAIN"})["description"])
        ambulance = self.post("ambulance").json()
        self.assertEqual(ambulance["step"], 2)
        self.assertEqual(ambulance["history"][1]["initial_route"], ORIGINAL)
        self.assertEqual(ambulance["history"][1]["initial_eta_min"], 20)
        self.assertEqual(ambulance["history"][1]["vehicle"], "SAMU-1")
        result = self.post("block")
        self.assertEqual(result.status_code, 200, result.text)
        self.assertEqual(result.json()["history"][2]["previous_route"], ORIGINAL)
        self.assertEqual(result.json()["history"][2]["new_route"], DETOUR)
        self.assertTrue(result.json()["history"][2]["rerouted"])
        self.assertEqual(result.json()["history"][2]["congestion"], {"R5": 2})
        self.assertEqual(result.json()["history"][2]["previous_eta_min"], 20)
        self.assertEqual(result.json()["history"][2]["new_eta_min"], 20)
        self.assertEqual(self.db.events.find_one({"type": "ROAD_BLOCKED"})["target_id"], "R2")
        self.assertEqual(self.post("power").json()["step"], 4)
        self.assertEqual(self.post("power").status_code, 409)
        self.assertEqual(self.db.events.count_documents({}), 3)
        self.assertEqual(self.client.get("/integration/scenario").json()["step"], 4)
        self.assertEqual(self.post("reset").json(), {"step": 0, "history": []})
        self.assertEqual(self.db.events.count_documents({}), 3)
        self.assertEqual(self.post("rain").status_code, 409)  # cible déjà sous pluie
        self.assertEqual(self.db.events.count_documents({}), 3)

    def test_no_ambulance_no_call(self):
        self.online = True
        self.post("rain")
        with patch("app.services.guided_scenario.fleet.available", return_value=[]):
            result = self.post("ambulance")
        self.assertEqual(result.status_code, 409)
        self.assertEqual(self.db.calls.count_documents({}), 0)
        self.assertEqual(self.client.get("/integration/scenario").json()["step"], 1)

    def test_pending_arrived_or_no_detour_creates_no_block(self):
        self.through_ambulance()
        self.db.calls.update_one({"call_id": "A-1"}, {"$unset": {"mission_id": ""}})
        self.assertEqual(self.post("block").status_code, 409)
        self.assertEqual(self.db.events.count_documents({"type": "ROAD_BLOCKED"}), 0)
        self.db.calls.update_one({"call_id": "A-1"}, {"$set": {"mission_id": "M-1"}})
        self.db.missions.update_one({"mission_id": "M-1"}, {"$set": {"status": "ARRIVED"}})
        self.assertEqual(self.post("block").status_code, 409)
        self.db.missions.update_one({"mission_id": "M-1"}, {"$set": {"status": "EN_ROUTE"}})
        with patch("app.services.guided_scenario.compute_route", side_effect=RuntimeError("pas de détour")):
            self.assertEqual(self.post("block").status_code, 409)
        self.assertEqual(self.db.events.count_documents({"type": "ROAD_BLOCKED"}), 0)
        self.assertEqual(self.client.get("/integration/scenario").json()["step"], 2)

    def test_no_road_behind_vehicle_is_blocked(self):
        self.through_ambulance()
        self.db.missions.update_one({"mission_id": "M-1"}, {"$set": {"progress": .76}})
        self.assertEqual(self.post("block").status_code, 409)
        self.assertEqual(self.db.events.count_documents({"type": "ROAD_BLOCKED"}), 0)


class MissionTrafficTests(unittest.TestCase):
    def setUp(self):
        self.db = mongomock.MongoClient().missions_test
        self.patcher = patch.object(mongo_client, "_db", self.db)
        self.patcher.start()
        self.doc = {"mission_id": "M-1", "profile": "AMBULANCE", "status": "EN_ROUTE",
                    "destination_id": "H1", "destination_name": "Hôpital", "route": ORIGINAL.copy(),
                    "route_names": ORIGINAL.copy(), "eta_min": 20,
                    "departure_at": datetime.now(timezone.utc), **{
                        k: v for k, v in route(ORIGINAL).items()
                        if k in ("path", "road_offsets", "distance_km", "avoided")}}
        self.db.missions.insert_one(self.doc.copy())

    def tearDown(self):
        self.patcher.stop()

    def test_bouchon_detourne_ambulance_et_persiste(self):
        with patch("app.services.missions._blocked_roads", return_value=set()), \
             patch("app.services.traffic.congestion_map", return_value={"R2": 3}), \
             patch("app.services.missions.compute_route", return_value=route(DETOUR)), \
             patch("app.services.simulation_activity.record"):
            result = missions._tick_mission(self.doc)
        self.assertEqual(result["status"], "DIVERTED")
        self.assertEqual(self.db.missions.find_one({"mission_id": "M-1"})["route"], DETOUR)
        self.assertTrue(any("Embouteillage" in item["message"] for item in result["timeline"]))

    def test_no_alternative_keeps_original_route(self):
        with patch("app.services.missions._blocked_roads", return_value=set()), \
             patch("app.services.traffic.congestion_map", return_value={"R2": 3}), \
             patch("app.services.missions.compute_route", return_value=route(ORIGINAL)):
            result = missions._tick_mission(self.doc)
        self.assertEqual(result["status"], "EN_ROUTE")
        self.assertEqual(result["route"], ORIGINAL)

    def test_blocked_road_reroutes_without_traffic(self):
        with patch("app.services.missions._blocked_roads", return_value={"R2"}), \
             patch("app.services.missions.compute_route", return_value=route(DETOUR)), \
             patch("app.services.simulation_activity.record"):
            result = missions._tick_mission(self.doc)
        self.assertEqual(result["status"], "DIVERTED")
        self.assertEqual(result["route"], DETOUR)


class RoutingPreviewTests(unittest.TestCase):
    def test_extra_blocked_previews_detour_without_mutating_active_state(self):
        roads = {rid: {"name": rid, "status": "CLEAR", "flood": 1,
                       "zone_id": "Z1", "zone_name": "Centre"}
                 for rid in ("R1", "R2", "R3", "R4")}
        edges = [{"src": a, "dst": b, "km": 1, "minutes": mins,
                  "traffic": 1, "flood": 1}
                 for a, b, mins in (("R1", "R2", 1), ("R2", "R4", 1),
                                    ("R1", "R3", 3), ("R3", "R4", 3))]
        active = set()

        def access(node, blocked):
            return (None, 0) if node in blocked else (node, 0)

        def graph(cypher, params=None):
            return [] if "r.path AS path" in cypher else [{"name": "route", "kind": "Road"}]

        with patch("app.services.routing._reseau", return_value=(roads, edges)), \
             patch("app.services.routing._active_dynamic_state", return_value=(active, set(), [])), \
             patch("app.services.routing._access_road", side_effect=access), \
             patch("app.services.routing.neo4j_client.query", side_effect=graph), \
             patch("app.services.traffic.congestion_map", return_value={}):
            base = routing.compute_route("R1", "R4")
            detour = routing.compute_route("R1", "R4", extra_blocked={"R2"})
            with self.assertRaises(RuntimeError):
                routing.compute_route("R1", "R4", extra_blocked={"R1"})
        self.assertEqual(base["route"], ["R1", "R2", "R4"])
        self.assertEqual(detour["route"], ["R1", "R3", "R4"])
        self.assertEqual(active, set())

    def test_variante_courte_optimise_distance_mais_annonce_un_temps(self):
        roads = {rid: {"name": rid, "status": "CLEAR", "flood": 1,
                       "zone_id": "Z1", "zone_name": "Centre"}
                 for rid in ("R1", "R2", "R3", "R4")}
        edges = [{"src": a, "dst": b, "km": km, "minutes": mins,
                  "traffic": 1, "flood": 1}
                 for a, b, km, mins in (("R1", "R2", 1, 10), ("R2", "R4", 1, 10),
                                        ("R1", "R3", 2, 1), ("R3", "R4", 2, 1))]
        with patch("app.services.routing._reseau", return_value=(roads, edges)), \
             patch("app.services.routing._active_dynamic_state", return_value=(set(), set(), [])), \
             patch("app.services.routing._access_road", side_effect=lambda node, blocked: (node, 0)), \
             patch("app.services.routing.neo4j_client.query", side_effect=lambda cypher, params=None:
                   [] if "r.path AS path" in cypher else [{"name": "route", "kind": "Road"}]), \
             patch("app.services.traffic.congestion_map", return_value={}):
            short = routing.compute_route("R1", "R4", mode="SHORT")
        self.assertEqual(short["route"], ["R1", "R2", "R4"])
        self.assertEqual(short["distance_km"], 2)
        self.assertEqual(short["estimated_time_min"], 16)


if __name__ == "__main__":
    unittest.main()
