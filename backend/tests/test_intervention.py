"""Projection de résolution : calcul en lecture seule, sans modifier la crise."""

import unittest
from unittest.mock import patch

from fastapi import HTTPException

from app.models.impact import ImpactNode, ImpactSummary
from app.routes.risk import preview_resolution
from app.services.cascade import build_impact


def impact(event_id, target, scores):
    nodes = [ImpactNode(id=ident, name=ident, kind="Hospital", depth=1, score=score)
             for ident, score in scores.items()]
    return ImpactSummary(
        event_id=event_id, event_type="ROAD_BLOCKED", severity="HIGH",
        target_id=target, impacts=nodes, direct_count=len(nodes),
        total_count=len(nodes), max_depth=1,
    )


class InterventionTests(unittest.TestCase):
    @patch("app.routes.risk.compute_impact")
    @patch("app.routes.risk.mongo_client.count_active_events", return_value=2)
    @patch("app.routes.risk.mongo_client.get_active_events", return_value=["e1", "e2"])
    def test_resolution_recalcule_les_autres_et_ne_les_additionne_pas(
        self, _events, _count, compute,
    ):
        def calcul(event_id, active_incidents):
            if event_id == "e1":
                return impact("e1", "R1", {"H4": 95, "T2": 60})
            return impact("e2", "Z1", {"H4": 75 if active_incidents == 2 else 60})

        compute.side_effect = calcul
        result = preview_resolution("e1")
        h4 = next(node for node in result["nodes"] if node["id"] == "H4")
        self.assertEqual((h4["before"], h4["after"], h4["reduction"]), (95, 60, 35))
        self.assertEqual(result["no_longer_exposed"], 1)  # T2 n'a plus de source
        self.assertEqual(result["changed_count"], 2)
        self.assertEqual(result["incidents_after"], 1)
        self.assertEqual(compute.call_count, 3)  # 2 avant + 1 après
        compute.assert_any_call("e2", active_incidents=1)

    @patch("app.routes.risk.mongo_client.get_active_events", return_value=[])
    def test_incident_non_actif_refuse(self, _events):
        with self.assertRaises(HTTPException) as exc:
            preview_resolution("inconnu")
        self.assertEqual(exc.exception.status_code, 404)

    @patch("app.services.cascade.score_node", return_value=(40, ["calculé"]))
    @patch("app.services.cascade._active_incidents")
    @patch("app.services.cascade._propagation_rows")
    def test_compteur_projete_est_utilise_sans_lire_les_incidents(
        self, rows, count, score,
    ):
        rows.return_value = [{
            "id": "H4", "kind": "Hospital", "name": "Hôpital H4",
            "depth": 1, "criticality": 4, "backup_power_hours": 2,
            "chain": [{"id": "R1"}, {"id": "H4"}],
        }]
        result = build_impact("ROAD_BLOCKED", "HIGH", "R1", "e1", active_incidents=1)
        count.assert_not_called()
        self.assertEqual(result.impacts[0].score, 40)
        self.assertEqual(score.call_args.kwargs["active_incidents"], 1)


if __name__ == "__main__":
    unittest.main()
