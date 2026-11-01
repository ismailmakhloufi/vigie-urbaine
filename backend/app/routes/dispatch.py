"""
Urban Butterfly - Console dispatcher : integration, flotte, actions

Sources agences (route standard) :
    POST /integration/fleet-updates : une flotte pousse l'etat d'un vehicule
    POST /integration/calls         : le CACU pousse un appel entrant
    POST /integration/calls/random  : simulateur de sources (demo)
Console :
    GET  /fleet                     : le registre de flotte
    POST /route-options             : comparateur (3 itineraires)
    POST /missions/{id}/corridor    : gyrophare
    POST /missions/{id}/radio       : canal radio
    POST /missions/{id}/choose-route: commande impose une variante
    POST /integration/demo          : orchestrateur de demo
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.services import demo, dispatcher, fleet, missions
from app.services.routing import compute_route_options


router = APIRouter()


class FleetUpdate(BaseModel):
    callsign: str
    type: str | None = None
    base_id: str | None = None
    status: str | None = None
    position: list[float] | None = None
    mission_id: str | None = None


class IncomingCall(BaseModel):
    kind: str = "MEDICAL"
    destination_id: str
    note: str = ""


class RouteOptionsRequest(BaseModel):
    origin_id: str
    destination_id: str
    profile: str = "AMBULANCE"


class CorridorRequest(BaseModel):
    minutes: int = Field(default=3, ge=1, le=10)


class RadioRequest(BaseModel):
    author: str = "CMD"
    text: str = Field(min_length=1, max_length=240)


class ChooseRouteRequest(BaseModel):
    variant: str = Field(pattern="^(FAST|SHORT|SAFE)$")


class DemoAction(BaseModel):
    action: str = Field(pattern="^(start|stop)$")


# ----- sources -----

@router.post("/integration/fleet-updates")
def fleet_updates(update: FleetUpdate):
    try:
        return fleet.integrate_fleet_update(update.model_dump(exclude_none=True))
    except (ValueError,) as exc:
        raise HTTPException(422, str(exc))


@router.post("/integration/calls")
def incoming_call(call: IncomingCall):
    try:
        return dispatcher.create_call(call.kind, call.destination_id, call.note)
    except LookupError as exc:
        raise HTTPException(404, str(exc))
    except RuntimeError as exc:
        raise HTTPException(409, str(exc))


@router.post("/integration/calls/random")
def random_call():
    try:
        return dispatcher.random_call()
    except RuntimeError as exc:
        raise HTTPException(409, str(exc))


@router.get("/integration/calls")
def calls(limit: int = 12):
    return dispatcher.list_calls(limit)


@router.post("/integration/demo")
def run_demo(action: DemoAction):
    if action.action == "start":
        return demo.start_demo()
    return demo.stop_demo()


@router.get("/integration/demo")
def demo_state():
    return demo.demo_status()


# ----- console -----

@router.get("/fleet")
def get_fleet():
    return fleet.list_fleet()


@router.post("/route-options")
def route_options(req: RouteOptionsRequest):
    try:
        return compute_route_options(req.origin_id, req.destination_id, req.profile)
    except LookupError as exc:
        raise HTTPException(404, str(exc))


@router.post("/missions/{mission_id}/corridor")
def mission_corridor(mission_id: str, req: CorridorRequest):
    try:
        return missions.snapshot(missions.activate_corridor(mission_id, req.minutes))
    except LookupError as exc:
        raise HTTPException(404, str(exc))
    except RuntimeError as exc:
        raise HTTPException(409, str(exc))


@router.post("/missions/{mission_id}/radio")
def mission_radio(mission_id: str, req: RadioRequest):
    try:
        return missions.snapshot(missions.radio(mission_id, req.author, req.text))
    except LookupError as exc:
        raise HTTPException(404, str(exc))


@router.post("/missions/{mission_id}/choose-route")
def mission_choose_route(mission_id: str, req: ChooseRouteRequest):
    try:
        return missions.snapshot(missions.choose_route(mission_id, req.variant))
    except LookupError as exc:
        raise HTTPException(404, str(exc))
    except RuntimeError as exc:
        raise HTTPException(409, str(exc))
