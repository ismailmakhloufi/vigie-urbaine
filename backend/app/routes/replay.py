"""Historique observé, jamais simulation contrefactuelle."""

from datetime import datetime

from fastapi import APIRouter, HTTPException, Query

from app.services.replay import get_snapshot, list_snapshots

router = APIRouter(prefix="/replay", tags=["Relecture"])


@router.get("")
def snapshots(limit: int = Query(default=120, ge=1, le=500), before: datetime | None = None):
    if before and before.tzinfo is None:
        raise HTTPException(422, "La date de pagination doit contenir un fuseau horaire")
    return {"snapshots": list_snapshots(limit, before),
            "retention_hours": 24,
            "note": "Observations enregistrées, sans recalcul historique. Les lectures des bases "
                    "sont réalisées dans une courte fenêtre, non simultanément."}


@router.get("/{snapshot_id}")
def snapshot(snapshot_id: str):
    doc = get_snapshot(snapshot_id)
    if doc is None:
        raise HTTPException(404, "Instantané introuvable ou expiré")
    return doc
