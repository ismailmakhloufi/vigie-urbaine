"""Observations avant/après résolution réelle, sans casser la résolution."""

import unittest
from unittest.mock import patch

from app.routes.events import resolve_event


def snapshot(incidents, score):
    return {
        "active_incidents": incidents,
        "counts_by_class": {"HIGH": int(score >= 50), "CRITICAL": 0},
        "nodes_at_risk": ([{"id": "H4", "name": "Hôpital H4", "score": score}]
                          if score else []),
    }


class RiskEvolutionTests(unittest.TestCase):
    @patch("app.db.mongo_client.mongo_client.record_risk_transition")
    @patch("app.db.mongo_client.mongo_client.set_event_status")
    @patch("app.routes.risk.risk_overview")
    @patch("app.db.mongo_client.mongo_client.get_event")
    def test_transition_enregistree_apres_resolution(
        self, get_event, overview, set_status, record,
    ):
        get_event.return_value = {"status": "ACTIVE", "type": "ROAD_BLOCKED",
                                  "target_id": "R1", "previous_status": None}
        overview.side_effect = [snapshot(2, 65), snapshot(1, 0)]
        response = resolve_event("e1")
        self.assertEqual(response["status"], "RESOLVED")
        set_status.assert_called_once_with("e1", "RESOLVED")
        transition = record.call_args.args[0]
        self.assertEqual((transition["before_high"], transition["after_high"]), (1, 0))
        self.assertEqual(transition["top_changes"][0]["after"], 0)

    @patch("app.db.mongo_client.mongo_client.set_event_status")
    @patch("app.routes.risk.risk_overview", side_effect=RuntimeError("risque indisponible"))
    @patch("app.db.mongo_client.mongo_client.get_event", return_value={
        "status": "ACTIVE", "type": "ROAD_BLOCKED", "target_id": "R1",
        "previous_status": None,
    })
    def test_risque_indisponible_ne_bloque_pas_la_resolution(self, _event, _risk, set_status):
        self.assertEqual(resolve_event("e1")["status"], "RESOLVED")
        set_status.assert_called_once_with("e1", "RESOLVED")


if __name__ == "__main__":
    unittest.main()
