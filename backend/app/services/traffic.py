"""
Urban Butterfly - Trafic vivant

L'embouteillage n'est pas plante au demarrage : il NAIT du chaos.
Un incident ROUTE_BLOQUE fait remonter la congestion sur les rues voisines
(CONNECTS_TO), la pluie alourdit les routes de sa zone. Chaque rue expose
un `bump` dynamique que le moteur de routage (et donc le dispatch et les
missions) applique en temps reel. Quand l'incident est resolu, la
congestion se resorbe d'elle-meme : rien n'est stocke.
"""

from app.db.mongo_client import mongo_client
from app.db.neo4j_client import neo4j_client


def congestion_map() -> dict[str, int]:
    """road_id -> bump de congestion (0 = fluide)."""
    bumps: dict[str, int] = {}

    events = mongo_client._db.events.find(
        {"status": {"$ne": "RESOLVED"}}, {"_id": 0, "type": 1, "target_id": 1, "severity": 1}
    )
    for ev in events:
        target = ev.get("target_id")
        if not target:
            continue
        severity = (ev.get("severity") or "HIGH").upper()

        if ev["type"] == "ROAD_BLOCKED":
            # la route bloquee versee son trafic sur ses voisines directes
            neighbors = neo4j_client.query(
                "MATCH (r:Road {id: $rid})-[c:CONNECTS_TO]-(n:Road) "
                "RETURN n.id AS id",
                {"rid": target},
            )
            weight = {"CRITICAL": 4, "HIGH": 3, "MEDIUM": 2, "LOW": 1}.get(severity, 3)
            for row in neighbors:
                rid = row["id"]
                bumps[rid] = bumps.get(rid, 0) + max(1, weight // 2)

    return bumps


def describe(bump: int) -> str:
    if bump >= 4:
        return "SATURÉ"
    if bump >= 2:
        return "EMBOUTILLAGE"
    if bump >= 1:
        return "CHARGÉ"
    return "FLUIDE"
