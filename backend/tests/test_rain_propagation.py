"""La pluie ne prouve pas une inondation de toutes les routes reliées."""

import unittest
from unittest.mock import patch

from app.services.cascade import _propagation_rows, build_impact
from app.services.risk import risk_class, score_node


class RainPropagationTests(unittest.TestCase):
    @patch("app.services.cascade.neo4j_client.query", return_value=[])
    def test_pas_de_propagation_routiere_hors_zone(self, query):
        _propagation_rows("HEAVY_RAIN", "Z1")
        cypher, params = query.call_args.args
        self.assertEqual(params, {"target_id": "Z1"})
        self.assertIn("[:LOCATED_IN]->(z)", cypher)
        self.assertNotIn("CONNECTED_BY", cypher)

    def test_pluie_ne_devient_pas_panne_electrique(self):
        score, reasons = score_node(
            kind="Hospital", depth=1, criticality=5, backup_power_hours=0,
            severity="CRITICAL", active_incidents=4, event_type="HEAVY_RAIN",
        )
        self.assertEqual((score, risk_class(score)), (40, "MEDIUM"))
        self.assertIn("inondation non constatée", reasons[0])
        self.assertFalse(any("secours électrique" in reason for reason in reasons))

    @patch("app.services.cascade._propagation_rows")
    def test_chaine_limitee_a_la_zone_et_au_site(self, rows):
        rows.return_value = [{
            "id": "H1", "kind": "Hospital", "name": "Hôpital", "depth": 1,
            "criticality": 5, "backup_power_hours": 0,
            "chain": [{"id": "Z1"}, {"id": "H1"}],
        }]
        impact = build_impact("HEAVY_RAIN", "HIGH", "Z1", None, active_incidents=1)
        self.assertEqual(impact.impacts[0].score, 35)
        self.assertEqual([n["id"] for n in impact.impacts[0].chain], ["Z1", "H1"])
