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
        return self._db.events.update_one(
            {"_id": ObjectId(event_id)}, {"$set": {"status": status}}
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

    def close(self):
        self._client.close()


mongo_client = MongoDbClient()
