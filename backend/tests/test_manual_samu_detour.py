"""Détour le plus court : prévisualisation sans incident et départ du tronçon courant."""

import unittest
from datetime import datetime, timezone
from unittest.mock import patch

import mongomock

from app.db.mongo_client import mongo_client
from app.services import missions


class ManualSamuDetourTests(unittest.TestCase):
    def setUp(self):
        self.db = mongomock.MongoClient().demo_test
        self.patcher = patch.object(mongo_client, "_db", self.db)
        self.patcher.start()
        self.doc = {
            "mission_id": "M-1", "status": "EN_ROUTE", "profile": "AMBULANCE",
            "destination_id": "H1", "route": ["R1", "R2", "R3", "R4"],
            "road_offsets": [{"end_km": 1}, {"end_km": 2},
                             {"end_km": 3}, {"end_km": 4}],
            "progress": 0.3, "timeline": [], "departure_at": datetime.now(timezone.utc),
        }

    def tearDown(self):
        self.patcher.stop()

    def test_candidats_uniquement_devant_et_avec_detour_court(self):
        def alternate(start, dest, profile, mode, extra_blocked):
            self.assertEqual((start, mode), ("R2", "SHORT"))
            self.assertEqual(extra_blocked, {"R3"})
            return {"route": ["R2", "R5", "R4"], "distance_km": 2.5,
                    "estimated_time_min": 8}
        with patch("app.services.missions.compute_route", side_effect=alternate) as route:
            candidates = missions.short_detour_candidates(self.doc)
        self.assertEqual([c["road_id"] for c in candidates], ["R3"])
        self.assertEqual(route.call_count, 1)
        self.assertEqual(self.db.events.count_documents({}), 0)

    def test_imposer_court_ne_repart_pas_de_r1(self):
        self.db.missions.insert_one(self.doc.copy())
        alternate = {"route": ["R2", "R5", "R4"], "route_names": ["R2", "R5", "R4"],
                     "avoided": [{"id": "R3"}], "distance_km": 2.5,
                     "estimated_time_min": 8, "path": [], "road_offsets": []}
        with patch("app.services.routing.compute_route", return_value=alternate) as route, \
             patch("app.services.simulation_activity.record"):
            updated = missions.choose_route("M-1", "SHORT")
        route.assert_called_once_with("R2", "H1", "AMBULANCE", mode="SHORT")
        self.assertEqual(updated["route"], ["R2", "R5", "R4"])
        self.assertEqual(self.db.missions.find_one({"mission_id": "M-1"})["route"], updated["route"])
