from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

EventType = Literal["POWER_FAILURE", "CYBER_ATTACK", "HEAVY_RAIN", "ROAD_BLOCKED"]
EventSeverity = Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"]


class EventCreate(BaseModel):
    type: EventType
    severity: EventSeverity
    target_id: str = Field(
        min_length=1,
        description="id of the infrastructure node affected (e.g. 'P1')",
    )
    description: str = ""
    payload: dict[str, Any] = Field(default_factory=dict)


class EventOut(BaseModel):
    id: str
    type: EventType
    severity: EventSeverity
    target_id: str
    description: str
    payload: dict[str, Any]
    timestamp: datetime
