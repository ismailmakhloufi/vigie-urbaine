"""
Urban Butterfly - Missions Router

POST /missions          : l'appel arrive, la mission demarre
GET  /missions          : instantane (positions, statuts, journaux)
POST /missions/{id}/cancel : annulation par le commandement
"""

from fastapi import APIRouter, HTTPException

from app.models.mission import MissionCreate, MissionSnapshot
from app.services.missions import cancel_mission, create_mission, list_missions, snapshot


router = APIRouter(prefix="/missions", tags=["Missions"])


@router.post("", response_model=MissionSnapshot)
def deploy(payload: MissionCreate):
    try:
        doc = create_mission(
            origin_id=payload.origin_id,
            destination_id=payload.destination_id,
            profile=payload.profile,
            caller_note=payload.caller_note,
        )
    except LookupError as exc:
        raise HTTPException(404, str(exc))
    except RuntimeError as exc:
        raise HTTPException(409, str(exc))
    return snapshot(doc)


@router.get("", response_model=list[MissionSnapshot])
def missions(limit: int = 30):
    return [snapshot(doc) for doc in list_missions(limit)]


@router.post("/{mission_id}/cancel", response_model=MissionSnapshot)
def cancel(mission_id: str):
    doc = cancel_mission(mission_id)
    if not doc:
        raise HTTPException(404, f"mission {mission_id} introuvable")
    return snapshot(doc)
