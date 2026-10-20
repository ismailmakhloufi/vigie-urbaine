"""
Urban Butterfly - Mission models (suivi SAMU / convois)

Une mission = un appel (POST /missions) + un vehicule qui progresse
le long du trajet calcule, avec detection de compromission en direct.
"""

from typing import Literal

from pydantic import BaseModel, Field

RoutingProfile = Literal["NORMAL", "AMBULANCE", "SUPPLY"]

MissionStatus = Literal["EN_ROUTE", "DIVERTED", "BLOCKED", "ARRIVED", "CANCELLED"]


class MissionCreate(BaseModel):
    origin_id: str = Field(min_length=1, description="Depart (dépôt, hôpital...)")
    destination_id: str = Field(min_length=1, description="Destination")
    profile: RoutingProfile = "AMBULANCE"
    caller_note: str = ""


class TimelineEntry(BaseModel):
    code: str
    message: str
    at: str


class MissionSnapshot(BaseModel):
    mission_id: str
    origin_id: str
    origin_name: str
    destination_id: str
    destination_name: str
    profile: RoutingProfile
    status: MissionStatus
    caller_note: str = ""
    route: list[str]
    route_names: list[str]
    avoided: list[dict] = []
    distance_km: float
    eta_min: int
    departure_at: str
    position: list[float] = []
    path: list[float] = []
    progress: float = 0.0
    remaining_min: int = 0
    timeline: list[TimelineEntry] = []
