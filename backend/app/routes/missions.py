"""
Urban Butterfly - Missions Router

GET  /missions               : instantane (positions, statuts, journaux)
POST /missions/{id}/cancel   : annulation par le commandement
Le dispatch passe par le service missions (console dispatcher).
"""

from fastapi import APIRouter, HTTPException

from app.models.mission import MissionSnapshot
from app.services.missions import cancel_mission, list_missions, snapshot


router = APIRouter(prefix="/missions", tags=["Missions"])


@router.get("", response_model=list[MissionSnapshot])
def missions(limit: int = 30):
    return [snapshot(doc) for doc in list_missions(limit)]


@router.post("/{mission_id}/cancel", response_model=MissionSnapshot)
def cancel(mission_id: str):
    doc = cancel_mission(mission_id)
    if not doc:
        raise HTTPException(404, f"mission {mission_id} introuvable")
    return snapshot(doc)
