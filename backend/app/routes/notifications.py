"""Centre de notifications persistant du poste de commandement."""

from typing import Literal

from fastapi import APIRouter, HTTPException, Query, Request

from app.services import notifications

router = APIRouter(prefix="/notifications", tags=["Notifications"])


@router.get("")
def inbox(limit: int = Query(default=30, ge=1, le=500),
          state: Literal["NEW", "ACKNOWLEDGED", "RESOLVED"] | None = None):
    return notifications.list_notifications(limit, state)


@router.post("/{notification_id}/acknowledge")
def acknowledge(notification_id: str, request: Request):
    actor = getattr(request.state, "actor", None)
    item = notifications.acknowledge(notification_id, (actor or {}).get("name", "operateur-demo"))
    if item is None:
        raise HTTPException(404, "Notification introuvable")
    return item
