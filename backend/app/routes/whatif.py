from fastapi import APIRouter, HTTPException

from app.db.neo4j_client import neo4j_client
from app.models.event import EventCreate
from app.models.impact import ImpactSummary
from app.services.cascade import compute_hypothetical

router = APIRouter(prefix="/whatif", tags=["What-if"])


@router.post("", response_model=ImpactSummary)
def what_if(event: EventCreate):
    """Simule un incident SANS rien ecrire dans les bases (dry-run).

    Le mode What-if repond a : 'et si cette panne arrivait maintenant ?'
    Aucun statut n'est modifie, aucun event n'est cree.
    """
    target = neo4j_client.query(
        "MATCH (t:Infrastructure {id: $target_id}) RETURN t.id AS id",
        {"target_id": event.target_id},
    )
    if not target:
        raise HTTPException(
            404, f"target '{event.target_id}' not found in the graph"
        )

    return compute_hypothetical(event.type, event.severity, event.target_id)
