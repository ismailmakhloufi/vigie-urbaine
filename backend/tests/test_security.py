"""Contrôles d'accès HTTP (pas seulement appels directs des fonctions)."""

import unittest
from types import SimpleNamespace
from unittest.mock import patch

from fastapi.testclient import TestClient

from app.main import app
from app.services.security import validate_config


SETTINGS = SimpleNamespace(
    security_mode="secure", auth_operator_password="phrase-secrete-longue",
    auth_viewer_password="autre-phrase-secrete", auth_agency_key="a" * 40,
    auth_cookie_secure=False,
)


class SecurityTests(unittest.TestCase):
    def setUp(self):
        self.config = patch("app.main.get_settings", return_value=SETTINGS)
        self.config.start()
        self.client = TestClient(app)

    def tearDown(self):
        self.client.close()
        self.config.stop()

    def test_acces_anonyme_refuse_et_origine_rejetee(self):
        self.assertEqual(self.client.get("/risk").status_code, 401)
        self.assertEqual(self.client.post("/integration/calls", json={},
            headers={"Origin": "https://site-etranger.example"}).status_code, 403)

    @patch("app.main.mongo_client._db")
    @patch("app.main.current_actor", return_value={"name": "observateur", "role": "viewer"})
    def test_observateur_lecture_seule_et_projection_autorisee(self, _actor, db):
        self.assertEqual(self.client.post("/integration/stream", json={"action": "pause"}).status_code, 403)
        with patch("app.routes.dispatch.compute_route_options", return_value={"options": []}):
            res = self.client.post("/route-options", json={
                "origin_id": "W1", "destination_id": "H1",
            })
        self.assertEqual(res.status_code, 200)
        self.assertEqual(db.audit_log.insert_one.call_count, 2)

    @patch("app.main.mongo_client._db")
    @patch("app.main.current_actor", return_value={"name": "observateur", "role": "viewer"})
    def test_observateur_peut_se_deconnecter(self, _actor, db):
        self.assertEqual(self.client.post("/auth/logout").status_code, 200)
        self.assertEqual(self.client.get("/auth/audit").status_code, 403)

    @patch("app.services.security.mongo_client._db")
    @patch("app.services.security.get_settings", return_value=SETTINGS)
    @patch("app.main.current_actor", return_value={"name": "operateur", "role": "operator"})
    def test_journal_operateur_limite(self, _actor, _settings, db):
        db.audit_log.find.return_value.sort.return_value.limit.return_value = []
        self.assertEqual(self.client.get("/auth/audit?limit=500").json(), [])
        db.audit_log.find.return_value.sort.return_value.limit.assert_called_once_with(100)

    @patch("app.routes.dispatch.dispatcher.create_call", return_value={"status": "PENDING"})
    @patch("app.main.mongo_client._db")
    def test_cle_agence_limitee_aux_entrees(self, db, create_call):
        headers = {"X-Agency-Key": SETTINGS.auth_agency_key}
        self.assertEqual(self.client.post("/integration/calls", json={"destination_id": "H1"},
            headers=headers).status_code, 200)
        self.assertEqual(self.client.get("/risk", headers=headers).status_code, 401)
        create_call.assert_called_once()
        self.assertEqual(db.audit_log.insert_one.call_args_list[0].args[0]["actor"], "agence")

    @patch("app.services.security.mongo_client._db")
    @patch("app.services.security.get_settings", return_value=SETTINGS)
    def test_login_cookie_opaque_et_pas_de_mot_de_passe_en_base(self, _settings, db):
        db.login_attempts.find_one.return_value = None
        res = self.client.post("/auth/login", json={
            "username": "operateur", "password": SETTINGS.auth_operator_password,
        })
        self.assertEqual(res.status_code, 200)
        self.assertIn("HttpOnly", res.headers["set-cookie"])
        self.assertIn("SameSite=strict", res.headers["set-cookie"])
        saved = db.sessions.insert_one.call_args.args[0]
        self.assertNotIn(SETTINGS.auth_operator_password, str(saved))
        self.assertEqual(saved["role"], "operator")

    @patch("app.services.security.mongo_client._db")
    @patch("app.services.security.get_settings", return_value=SETTINGS)
    def test_cycle_connexion_session_deconnexion(self, _settings, db):
        sessions = {}
        db.login_attempts.find_one.return_value = None
        db.sessions.insert_one.side_effect = lambda doc: sessions.update({doc["_id"]: doc})
        db.sessions.find_one.side_effect = lambda query: sessions.get(query["_id"])
        db.sessions.delete_one.side_effect = lambda query: sessions.pop(query["_id"], None)
        res = self.client.post("/auth/login", json={"username": "operateur",
            "password": SETTINGS.auth_operator_password})
        self.assertEqual(res.status_code, 200)
        self.assertEqual(self.client.get("/auth/me").json()["role"], "operator")
        self.assertEqual(self.client.post("/auth/logout").status_code, 200)
        self.assertEqual(self.client.get("/auth/me").status_code, 401)

    @patch("app.services.security.get_settings", return_value=SimpleNamespace(
        security_mode="secure", auth_operator_password="short", auth_agency_key="bad",
        auth_viewer_password="",
    ))
    def test_secrets_obligatoires_en_mode_securise(self, _settings):
        with self.assertRaises(RuntimeError):
            validate_config()


if __name__ == "__main__":
    unittest.main()
