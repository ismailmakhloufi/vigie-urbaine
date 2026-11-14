from bson import ObjectId
from pymongo import MongoClient

from app.core.config import get_settings


class MongoDbClient:
    def __init__(self):
        settings = get_settings()
        self._client = MongoClient(settings.mongo_uri, serverSelectionTimeoutMS=3000)
        self._db = self._client[settings.mongo_db]

    def verify(self) -> bool:
        self._client.admin.command("ping")
        return True

    def insert_event(self, event: dict):
        return self._db.events.insert_one(event)

    def get_event(self, event_id: str):
        try:
            event = self._db.events.find_one({"_id": ObjectId(event_id)})
        except Exception:
            return None
        if event:
            event.pop("_id", None)
        return event

    def set_event_status(self, event_id: str, status: str):
        from datetime import datetime, timezone
        fields = {"status": status}
        if status == "RESOLVED":
            fields["resolved_at"] = datetime.now(timezone.utc)
        return self._db.events.update_one(
            {"_id": ObjectId(event_id)}, {"$set": fields}
        )

    def auto_resolve_events(self) -> list[dict]:
        return list(self._db.events.find(
            {"status": "ACTIVE", "auto_resolve_at": {"$exists": True}},
            {"_id": 1, "auto_resolve_at": 1},
        ))

    def restore_legacy_auto_resolve(self, duration_seconds: int):
        """Rattrape les incidents simulés créés avant la persistance des échéances."""
        from datetime import datetime, timedelta, timezone

        query = {"status": "ACTIVE", "auto_resolve_at": {"$exists": False},
                 "$or": [
                     {"payload.source": {"$in": ["flux-automatique", "virtual-siem", "virtual-scada"]}},
                     {"description": {"$regex": r"^Meteo reelle zone"}},
                 ]}
        now = datetime.now(timezone.utc)
        for event in self._db.events.find(query, {"timestamp": 1}):
            if event.get("timestamp"):
                timestamp = event["timestamp"]
                if timestamp.tzinfo is None:
                    timestamp = timestamp.replace(tzinfo=timezone.utc)
                # Les anciens incidents n'ont pas d'échéance connue : ne pas
                # résoudre toute la crise d'un coup au premier redémarrage.
                deadline = max(timestamp, now) + timedelta(seconds=duration_seconds)
                self._db.events.update_one(
                    {"_id": event["_id"], "status": "ACTIVE", "auto_resolve_at": {"$exists": False}},
                    {"$set": {"auto_resolve_at": deadline}},
                )

    def count_active_events(self) -> int:
        return self._db.events.count_documents({"status": {"$ne": "RESOLVED"}})

    def get_active_events(self, limit: int = 100) -> list[dict]:
        events = (
            self._db.events.find({"status": {"$ne": "RESOLVED"}}, {"_id": 1})
            .sort("timestamp", -1)
            .limit(limit)
        )
        return [str(e["_id"]) for e in events]

    def list_events(self, limit: int = 50) -> list[dict]:
        events = self._db.events.find({}, {"_id": 0}).sort("timestamp", -1).limit(limit)
        return list(events)

    def record_risk_transition(self, transition: dict):
        self._db.risk_transitions.insert_one(transition)

    def list_risk_transitions(self, limit: int = 12) -> list[dict]:
        return list(self._db.risk_transitions.find({}, {"_id": 0})
                    .sort("recorded_at", -1).limit(limit))

    def insert_mission(self, mission: dict):
        return self._db.missions.insert_one(mission)

    def get_mission(self, mission_id: str) -> dict | None:
        return self._db.missions.find_one({"mission_id": mission_id})

    def active_missions(self) -> list[dict]:
        return list(
            self._db.missions.find({"status": {"$in": ["EN_ROUTE", "DIVERTED"]}})
            .sort("departure_at", 1)
        )

    def all_missions(self, limit: int = 30) -> list[dict]:
        return list(
            self._db.missions.find().sort("departure_at", -1).limit(limit)
        )

    def update_mission(self, mission_id: str, fields: dict):
        return self._db.missions.update_one(
            {"mission_id": mission_id}, {"$set": fields}
        )

    def count_missions(self) -> int:
        return self._db.missions.count_documents({})

    # ----- compteur sequentiel (IDs atomiques) -----

    def _amorcer_compteur(self, cle: str, collection: str, champ: str):
        """Au premier appel : le compteur repart du plus haut numero deja utilise."""
        col = self._db[collection]
        dernier = 0
        for doc in col.find({}, {champ: 1}):
            ident = str(doc.get(champ) or "")
            suffixe = ident.rsplit("-", 1)[-1]
            if suffixe.isdigit():
                dernier = max(dernier, int(suffixe))
        self._db.counters.update_one(
            {"_id": cle}, {"$set": {"seq": dernier}}, upsert=True
        )

    def sequence(self, cle: str, collection: str, champ: str) -> int:
        """Increment atomique d'un compteur nomme ($inc) — IDs sans collision."""
        col = self._db.counters
        if col.find_one({"_id": cle}) is None:
            self._amorcer_compteur(cle, collection, champ)
        doc = col.find_one_and_update(
            {"_id": cle}, {"$inc": {"seq": 1}},
            upsert=True, return_document=True,
        )
        return doc["seq"]

    # ----- flotte (registry vehicules) -----

    def insert_vehicle(self, vehicle: dict):
        return self._db.vehicles.update_one(
            {"callsign": vehicle["callsign"]}, {"$setOnInsert": vehicle}, upsert=True
        )

    def upsert_vehicle(self, callsign: str, fields: dict):
        return self._db.vehicles.update_one(
            {"callsign": callsign}, {"$set": fields}, upsert=True
        )

    def reserve_vehicle(self, callsign: str, reservation: str) -> bool:
        """Une seule transition AVAILABLE -> RESERVED peut gagner."""
        result = self._db.vehicles.update_one(
            {"callsign": callsign, "status": "AVAILABLE"},
            {"$set": {"status": "RESERVED", "reservation": reservation}},
        )
        return result.modified_count == 1

    def commit_vehicle(self, callsign: str, reservation: str, mission_id: str) -> bool:
        result = self._db.vehicles.update_one(
            {"callsign": callsign, "status": "RESERVED", "reservation": reservation},
            {"$set": {"status": "ON_MISSION", "mission_id": mission_id},
             "$unset": {"reservation": ""}},
        )
        return result.modified_count == 1

    def cancel_vehicle_reservation(self, callsign: str, reservation: str):
        return self._db.vehicles.update_one(
            {"callsign": callsign, "status": "RESERVED", "reservation": reservation},
            {"$set": {"status": "AVAILABLE"}, "$unset": {"reservation": ""}},
        )

    def list_vehicles(self) -> list[dict]:
        return list(self._db.vehicles.find().sort("callsign", 1))

    def count_vehicles(self) -> int:
        return self._db.vehicles.count_documents({})

    # ----- appels (centre d'appel) -----

    def insert_call(self, call: dict):
        return self._db.calls.insert_one(call)

    def update_call(self, call_id: str, fields: dict):
        return self._db.calls.update_one({"call_id": call_id}, {"$set": fields})

    def list_calls(self, limit: int = 15) -> list[dict]:
        return list(
            self._db.calls.find().sort("created_at", -1).limit(limit)
        )

    def close(self):
        self._client.close()


mongo_client = MongoDbClient()
