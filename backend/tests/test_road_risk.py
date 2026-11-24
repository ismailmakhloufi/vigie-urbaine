"""Un blocage routier affecte l'accès local, pas la santé intrinsèque d'un site."""

import unittest
from unittest.mock import patch

from app.services.cascade import _propagation_rows, build_impact
from app.services.risk import risk_class, score_node


class RoadRiskTests(unittest.TestCase):
    @patch("app.services.cascade.neo4j_client.query", return_value=[])
    def test_le_graphe_ne_propage_pas_un_blocage_sur_cinq_routes(self, query):
        _propagation_rows("ROAD_BLOCKED", "R1")
        cypher, params = query.call_args.args
        self.assertEqual(params, {"target_id": "R1", "max_access_distance_m": 5000})
        self.assertIn("MATCH (x:Infrastructure)-[:CONNECTED_BY]->(r)", cypher)
        self.assertIn("MATCH (warehouse:Warehouse:Infrastructure)-[:CONNECTED_BY]->(r)", cypher)
        self.assertIn("alternative <> r", cypher)
        self.assertIn("point.distance", cypher)
        self.assertNotIn("CONNECTED_BY*", cypher)

    def test_pharmacie_accessible_seulement_par_la_route_bloquee(self):
        score, reasons = score_node(
            kind="Pharmacy", depth=1, criticality=2,
            backup_power_hours=None, severity="CRITICAL",
            active_incidents=8, event_type="ROAD_BLOCKED",
        )
        self.assertEqual((score, risk_class(score)), (35, "MEDIUM"))
        self.assertIn("accès routier direct", reasons[0])
        self.assertFalse(any("secours électrique" in reason for reason in reasons))

    def test_approvisionnement_n_est_pas_une_panne_de_pharmacie(self):
        score, reasons = score_node(
            kind="Pharmacy", depth=2, criticality=2,
            backup_power_hours=None, severity="HIGH",
            active_incidents=3, event_type="ROAD_BLOCKED",
        )
        self.assertEqual((score, risk_class(score)), (15, "LOW"))
        self.assertIn("approvisionnement potentiellement retardé", reasons[0])

    @patch("app.services.cascade._propagation_rows")
    def test_impact_et_whatif_utilisent_la_meme_regle(self, rows):
        rows.return_value = [{
            "id": "PH1", "kind": "Pharmacy", "name": "Pharmacie",
            "depth": 1, "criticality": 2, "backup_power_hours": None,
            "chain": [{"id": "R1"}, {"id": "PH1"}],
        }]
        impact = build_impact("ROAD_BLOCKED", "HIGH", "R1", "evt", active_incidents=1)
        whatif = build_impact("ROAD_BLOCKED", "HIGH", "R1", None, active_incidents=1)
        self.assertEqual((impact.impacts[0].score, impact.impacts[0].risk), (30, "MEDIUM"))
        self.assertEqual(impact.impacts[0].score, whatif.impacts[0].score)

    def test_panne_electrique_garde_le_score_technique(self):
        score, _ = score_node(
            kind="Hospital", depth=1, criticality=4,
            backup_power_hours=0, severity="HIGH",
            active_incidents=2, event_type="POWER_FAILURE",
        )
        self.assertEqual(score, 95)


if __name__ == "__main__":
    unittest.main()
