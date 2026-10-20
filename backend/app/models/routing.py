"""
Urban Butterfly - Routing models (etape routing)

Requete :
    {"origin_id": "W1", "destination_id": "H1", "profile": "AMBULANCE"}

Reponse : chemin en routes, temps estime, routes evitees + raisons.
"""

from typing import Literal

from pydantic import BaseModel, Field

RoutingProfile = Literal["NORMAL", "AMBULANCE", "SUPPLY"]


class RouteRequest(BaseModel):
    origin_id: str = Field(min_length=1, description="Infrastructure de depart (W1...)")
    destination_id: str = Field(min_length=1, description="Infrastructure d'arrivee (H1...)")
    profile: RoutingProfile = "AMBULANCE"


class AvoidedRoad(BaseModel):
    id: str
    reason: str


class RouteResponse(BaseModel):
    origin_id: str
    origin_name: str
    destination_id: str
    destination_name: str
    profile: RoutingProfile
    route: list[str]
    route_names: list[str]
    estimated_time_min: int
    distance_km: float
    avoided: list[AvoidedRoad]
    dynamic_notes: list[str]
