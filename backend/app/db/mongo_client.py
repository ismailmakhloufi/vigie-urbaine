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

    def list_events(self, limit: int = 50) -> list[dict]:
        events = self._db.events.find({}, {"_id": 0}).sort("timestamp", -1).limit(limit)
        return list(events)

    def close(self):
        self._client.close()


mongo_client = MongoDbClient()
