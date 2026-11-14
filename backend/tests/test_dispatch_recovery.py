"""Réservation concurrente, file d'appels et reprise des échéances."""

import threading
import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

from app.services import dispatcher, sources
from app.services.missions import RouteUnavailable
from app.db.mongo_client import mongo_client


class DispatchRecoveryTests(unittest.TestCase):
    @patch("app.db.mongo_client.mongo_client._db")
    def test_reservation_mongo_conditionnelle_sans_upsert(self, db):
        db.vehicles.update_one.return_value.modified_count = 1
        self.assertTrue(mongo_client.reserve_vehicle("SAMU-9", "A-1"))
        args, kwargs = db.vehicles.update_one.call_args
        self.assertEqual(args[0], {"callsign": "SAMU-9", "status": "AVAILABLE"})
        self.assertEqual(args[1]["$set"]["reservation"], "A-1")
        self.assertNotIn("upsert", kwargs)
        mongo_client.cancel_vehicle_reservation("SAMU-9", "A-1")
        self.assertEqual(db.vehicles.update_one.call_args.args[0]["reservation"], "A-1")

    @patch("app.services.dispatcher.create_mission")
    @patch("app.services.dispatcher.fleet.cancel_reservation")
    @patch("app.services.dispatcher.fleet.assign")
    @patch("app.services.dispatcher.fleet.reserve")
    @patch("app.services.dispatcher._candidats")
    def test_deux_appels_concurrents_ne_partagent_pas_le_vehicule(
        self, candidates, reserve, assign, cancel, create,
    ):
        candidates.return_value = [{"callsign": "SAMU-9", "base_id": "W1"}]
        lock = threading.Lock()
        barrier = threading.Barrier(2)
        owned = set()

        def atomic_reserve(_vehicle, call_id):
            barrier.wait(timeout=3)
            with lock:
                if owned:
                    return False
                owned.add(call_id)
                return True

        reserve.side_effect = atomic_reserve
        create.return_value = {"mission_id": "M-1"}
        assign.return_value = True
        results = []

        def run(index):
            results.append(dispatcher._dispatch(
                {"call_id": f"A-{index}", "kind": "MEDICAL", "destination_id": "H1"},
                [36.8, 10.2],
            )[0])

        workers = [threading.Thread(target=run, args=(i,)) for i in range(2)]
        for worker in workers:
            worker.start()
        for worker in workers:
            worker.join(timeout=5)
        self.assertEqual(sorted(results), ["DISPATCHED", "PENDING"])
        create.assert_called_once()
        assign.assert_called_once()

    @patch("app.services.dispatcher.create_mission", side_effect=RouteUnavailable("route bloquée"))
    @patch("app.services.dispatcher.fleet.cancel_reservation")
    @patch("app.services.dispatcher.fleet.reserve", return_value=True)
    @patch("app.services.dispatcher._candidats", return_value=[{"callsign": "SAMU-9", "base_id": "W1"}])
    def test_route_bloquee_libere_reservation(self, _candidates, _reserve, cancel, _create):
        status, _, _ = dispatcher._dispatch(
            {"call_id": "A-1", "kind": "MEDICAL", "destination_id": "H1"}, [36.8, 10.2],
        )
        self.assertEqual(status, "ROUTE_UNAVAILABLE")
        cancel.assert_called_once_with("SAMU-9", "A-1")

    @patch("app.services.dispatcher.create_mission", side_effect=OSError("Mongo indisponible"))
    @patch("app.services.dispatcher.fleet.cancel_reservation")
    @patch("app.services.dispatcher.fleet.reserve", return_value=True)
    @patch("app.services.dispatcher._candidats", return_value=[{"callsign": "SAMU-9", "base_id": "W1"}])
    def test_echec_ecriture_libere_reservation_sans_accuser_la_route(
        self, _candidates, _reserve, cancel, _create,
    ):
        with self.assertRaises(OSError):
            dispatcher._dispatch({"call_id": "A-1", "kind": "MEDICAL",
                                  "destination_id": "H1"}, [36.8, 10.2])
        cancel.assert_called_once_with("SAMU-9", "A-1")

    @patch("app.services.dispatcher.mongo_client.update_call")
    @patch("app.services.dispatcher._dispatch", return_value=("ROUTE_UNAVAILABLE", None, None))
    @patch("app.services.dispatcher._coords_of", return_value=[36.8, 10.2])
    @patch("app.services.dispatcher.mongo_client._db")
    def test_route_inaccessible_reste_reessayable(self, db, _coords, _dispatch, update):
        db.calls.find.return_value = [{"call_id": "A-1", "kind": "MEDICAL", "destination_id": "H1",
                                       "status": "ROUTE_UNAVAILABLE", "queue_tries": 15}]
        db.missions.find_one.return_value = None
        dispatcher._file_traiter()
        self.assertEqual(update.call_args.args[1]["status"], "ROUTE_UNAVAILABLE")
        self.assertEqual(update.call_args.args[1]["queue_tries"], 0)

    @patch("app.services.dispatcher.fleet.cancel_reservation")
    @patch("app.services.dispatcher.fleet.assign", return_value=True)
    @patch("app.services.dispatcher.mongo_client.update_call")
    @patch("app.services.dispatcher.mongo_client._db")
    def test_reprise_reservation_avec_mission_deja_creee(self, db, update, assign, cancel):
        db.vehicles.find.return_value = [{"callsign": "SAMU-9", "reservation": "A-1"}]
        db.missions.find_one.return_value = {"mission_id": "M-1"}
        dispatcher.recover_reservations()
        assign.assert_called_once_with("SAMU-9", "M-1", "A-1")
        self.assertEqual(update.call_args.args[1]["status"], "DISPATCHED")
        cancel.assert_not_called()

    @patch("app.services.sources.mongo_client.auto_resolve_events")
    @patch("app.services.sources.mongo_client.restore_legacy_auto_resolve")
    def test_reprise_apres_redemarrage(self, migrate, read_events):
        deadline = datetime.now(timezone.utc) - timedelta(seconds=1)
        read_events.return_value = [{"_id": "e1", "auto_resolve_at": deadline}]
        with sources._lock:
            sources._pending[:] = []
        sources._restore_pending()
        migrate.assert_called_once_with(sources.RESOLVE_AFTER[1])
        self.assertEqual(sources._pending[0][0], "e1")
        with patch("app.routes.events.resolve_event", side_effect=[RuntimeError("temporaire"), {}]) as resolve:
            sources._resolve_expired()
            self.assertEqual(len(sources._pending), 1)
            sources._resolve_expired()
            self.assertEqual(len(sources._pending), 0)
            self.assertEqual(resolve.call_count, 2)


if __name__ == "__main__":
    unittest.main()
