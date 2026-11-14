"""Contrats de provenance de la vue des risques (sans base de données)."""

import unittest
from unittest.mock import patch

from app.models.impact import ImpactNode, ImpactSummary
from app.routes.risk import risk_overview


def impact(event_id, target, score, depth, chain):
    node = ImpactNode(
        id="H4", kind="Hospital", name="Hôpital H4", depth=depth,
        score=score, risk="CRITICAL" if score >= 70 else "HIGH",
        reasons=[f"raison {event_id}"], chain=chain,
    )
    return ImpactSummary(
        event_id=event_id, event_type="ROAD_BLOCKED", severity="HIGH",
        target_id=target, impacts=[node], direct_count=int(depth == 1),
        total_count=1, max_depth=depth,
    )


class RiskProvenanceTests(unittest.TestCase):
    @patch("app.routes.risk.compute_impact")
    @patch("app.routes.risk.mongo_client.get_active_events")
    def test_sources_preservees_et_score_maximum(self, active_events, compute):
        active_events.return_value = ["e1", "e2"]
        compute.side_effect = [
            impact("e1", "R1", 55, 2, [{"id": "R1"}, {"id": "W1"}, {"id": "H4"}]),
            impact("e2", "R2", 85, 1, [{"id": "R2"}, {"id": "H4"}]),
        ]

        overview = risk_overview()
        node = overview["nodes_at_risk"][0]
        self.assertEqual(node["score"], 85)
        self.assertEqual(node["main_event_id"], "e2")
        self.assertEqual([s["event_id"] for s in node["sources"]], ["e2", "e1"])
        self.assertEqual(node["sources"][1]["chain"][-1]["id"], "H4")
        self.assertEqual(node["sources"][0]["reasons"], ["raison e2"])

    @patch("app.routes.risk.mongo_client.get_active_events", return_value=[])
    def test_aucun_incident(self, _active_events):
        self.assertEqual(risk_overview()["nodes_at_risk"], [])


if __name__ == "__main__":
    unittest.main()
