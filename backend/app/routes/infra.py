from fastapi import APIRouter

from app.db.neo4j_client import neo4j_client

router = APIRouter(prefix="/infrastructure", tags=["City"])


@router.get("")
def infrastructure():
    rows = neo4j_client.query(
        "MATCH (n:Infrastructure) "
        "RETURN n.id AS id, n.kind AS kind, n.name AS name, "
        "n.lat AS lat, n.lon AS lon, n.status AS status, "
        "n.criticality AS criticality, "
        "n.backup_power_hours AS backup_power_hours, "
        "n.medicine_stock_days AS stock_days, "
        "n.path AS path "
        "ORDER BY n.kind, n.id"
    )
    return rows
