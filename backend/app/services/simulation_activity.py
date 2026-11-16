"""Journal lisible des actions du simulateur, séparé des notifications métier."""

import logging
from datetime import datetime, timezone

from bson import ObjectId
from bson.errors import InvalidId

from app.db.mongo_client import mongo_client

logger = logging.getLogger(__name__)


def ensure_indexes():
    mongo_client._db.simulation_activity.create_index([("at", -1)])


def record(action: str, message: str, source: str = "simulateur", reference: str | None = None):
    try:
        mongo_client._db.simulation_activity.insert_one({
            "at": datetime.now(timezone.utc), "action": action,
            "message": message, "source": source, "reference": reference,
        })
    except Exception:
        logger.exception("Écriture du journal de simulation indisponible")


def recent(limit: int = 60, before_at: datetime | None = None,
           before_id: str | None = None) -> list[dict]:
    query = {}
    if before_at and before_id:
        try:
            ident = ObjectId(before_id)
        except (InvalidId, TypeError):
            return []
        if before_at.tzinfo:
            before_at = before_at.astimezone(timezone.utc).replace(tzinfo=None)
        query = {"$or": [{"at": {"$lt": before_at}},
                         {"at": before_at, "_id": {"$lt": ident}}]}
    rows = mongo_client._db.simulation_activity.find(query).sort([("at", -1), ("_id", -1)]).limit(limit)
    return [{**{key: value for key, value in row.items() if key != "_id"},
             "at": row["at"].replace(tzinfo=timezone.utc).isoformat()
             if row["at"].tzinfo is None else row["at"].isoformat(),
             "id": str(row["_id"])} for row in rows]
