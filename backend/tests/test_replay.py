"""Archives immuables, pagination et absence de recalcul à la lecture."""

import unittest
from datetime import datetime, timezone
from unittest.mock import patch

from fastapi import HTTPException

from app.routes.replay import snapshot, snapshots
from app.services import replay


class ReplayTests(unittest.TestCase):
    @patch("app.routes.infra.infrastructure", return_value=[
        {"id": "H1", "status": "OFFLINE"}, {"id": "R1", "status": "BLOCKED"}])
    @patch("app.routes.risk.risk_overview", return_value={
        "active_incidents": 1, "nodes_at_risk": [{"id": "H1", "score": 80}],
        "incident_list": [], "counts_by_class": {"HIGH": 1}})
    @patch("app.services.replay.mongo_client")
    def test_capture_archive_faits_sans_resoudre_incident(self, mongo, _risk, _infra):
        mongo.list_vehicles.return_value = [{"callsign": "SAMU-9", "status": "AVAILABLE"}]
        mongo.list_calls.return_value = []
        mongo._db.missions.find.return_value.sort.return_value.limit.return_value = []
        mongo._db.crisis_snapshots.insert_one.return_value.inserted_id = "archive-1"
        self.assertEqual(replay.capture()["id"], "archive-1")
        saved = mongo._db.crisis_snapshots.insert_one.call_args.args[0]
        self.assertEqual(saved["risk"]["nodes_at_risk"][0]["score"], 80)
        self.assertEqual(saved["infrastructure_status"]["R1"], "BLOCKED")
        self.assertLessEqual(saved["started_at"], saved["captured_at"])
        mongo._db.events.update_one.assert_not_called()
        mongo._db.missions.update_one.assert_not_called()

    @patch("app.services.replay.mongo_client")
    def test_lecture_archive_sans_recalcul(self, mongo):
        ident = "507f1f77bcf86cd799439011"
        mongo._db.crisis_snapshots.find_one.return_value = {"risk": {"active_incidents": 2}}
        self.assertEqual(replay.get_snapshot(ident)["risk"]["active_incidents"], 2)
        self.assertIsNone(replay.get_snapshot("id invalide"))
        mongo._db.crisis_snapshots.find_one.assert_called_once()

    @patch("app.routes.replay.list_snapshots", return_value=[])
    def test_pagination_exige_date_avec_fuseau(self, _list):
        with self.assertRaises(HTTPException) as context:
            snapshots(limit=5, before=datetime(2026, 1, 1))
        self.assertEqual(context.exception.status_code, 422)
        self.assertEqual(snapshots(limit=5, before=datetime.now(timezone.utc))["snapshots"], [])

    @patch("app.routes.replay.get_snapshot", return_value=None)
    def test_archive_inconnue_renvoie_404(self, _get):
        with self.assertRaises(HTTPException) as context:
            snapshot("invalide")
        self.assertEqual(context.exception.status_code, 404)


if __name__ == "__main__":
    unittest.main()
