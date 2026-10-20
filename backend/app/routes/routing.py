"""
Urban Butterfly - Routing Router

POST /routing : itineraire optimal dynamique (incidents actifs inclus).
"""

from fastapi import APIRouter, HTTPException

from app.models.routing import RouteRequest, RouteResponse
from app.services.routing import compute_route


router = APIRouter(prefix="/routing", tags=["Routing"])


@router.post("", response_model=RouteResponse)
def route(request: RouteRequest):
    try:
        return compute_route(
            origin_id=request.origin_id,
            destination_id=request.destination_id,
            profile=request.profile,
        )
    except LookupError as exc:
        raise HTTPException(404, str(exc))
    except RuntimeError as exc:
        raise HTTPException(409, str(exc))
