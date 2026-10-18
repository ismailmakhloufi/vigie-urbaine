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

    def list_events(self, limit: int = 50) -> list[dict]:
        events = self._db.events.find({}, {"_id": 0}).sort("timestamp", -1).limit(limit)
        return list(events)

    def close(self):
        self._client.close()


mongo_client = MongoDbClient()
