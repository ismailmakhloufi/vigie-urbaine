from contextlib import asynccontextmanager
import logging
import secrets
from datetime import datetime, timezone

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.db.mongo_client import mongo_client
from app.db.neo4j_client import neo4j_client
from app.routes.events import router as events_router
from app.routes.infra import router as infra_router
from app.routes.risk import router as risk_router
from app.routes.whatif import router as whatif_router
from app.routes.missions import router as missions_router
from app.routes.dispatch import router as dispatch_router
from app.routes.ai import router as ai_router
from app.routes.replay import router as replay_router
from app.routes.notifications import router as notifications_router
from app.services import sources
from app.services import dispatcher as dispatcher_service
from app.services import replay
from app.services import notifications
from app.services import source_health
from app.services.security import (router as auth_router, validate_config,
                                   current_actor, allowed_origins)
from app.core.config import get_settings

logger = logging.getLogger(__name__)


def _audit(request, actor, status):
    try:
        mongo_client._db.audit_log.insert_one({
            "at": datetime.now(timezone.utc), "actor": (actor or {}).get("name", "anonymous"),
            "role": (actor or {}).get("role"), "method": request.method,
            "path": request.url.path, "status": status,
        })
    except Exception:
        logger.exception("Échec de journalisation de l'action")


@asynccontextmanager
async def lifespan(app: FastAPI):
    validate_config()
    if get_settings().security_mode == "demo":
        logger.warning("MODE DEMONSTRATION : API non authentifiée ; ne pas exposer sur Internet")
    else:
        mongo_client._db.sessions.create_index("expires_at", expireAfterSeconds=0)
        mongo_client._db.login_attempts.create_index("until", expireAfterSeconds=0)
    notifications.ensure_indexes()
    source_health.ensure_indexes()
    notifications.reconcile_current()
    # le monde s'agite des qu'on demarre : flux agences en ligne
    sources.start_stream()
    # file d'attente des appels sans vehicule : rappel automatique
    dispatcher_service.start_queue()
    replay.start_recorder()
    yield
    replay.stop_recorder()
    sources.stop_stream()
    neo4j_client.close()
    mongo_client.close()


app = FastAPI(
    title="Urban Butterfly API",
    description="Intelligent Urban Cascade Risk Simulator",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=sorted(allowed_origins()),
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def secure_console(request, call_next):
    path = request.url.path
    settings = get_settings()
    secure = settings.security_mode == "secure"
    unsafe = request.method not in ("GET", "HEAD", "OPTIONS")
    actor = None
    if not secure and request.client and request.client.host not in ("127.0.0.1", "::1", "localhost", "testclient"):
        return JSONResponse({"detail": "Mode démonstration limité à la machine locale"}, status_code=403)
    if secure:
        origin = request.headers.get("origin")
        if unsafe and origin and origin not in allowed_origins():
            _audit(request, actor, 403)
            return JSONResponse({"detail": "Origine non autorisée"}, status_code=403)
        public = path in ("/", "/health", "/auth/config", "/auth/login")
        agency = path in ("/integration/calls", "/integration/fleet-updates") and request.method == "POST"
        if not public:
            if agency and request.headers.get("x-agency-key") and secrets.compare_digest(
                request.headers["x-agency-key"], settings.auth_agency_key):
                actor = {"name": "agence", "role": "agency"}
            else:
                actor = current_actor(request)
                if not actor:
                    _audit(request, None, 401)
                    return JSONResponse({"detail": "Connexion requise"}, status_code=401)
                if path == "/auth/audit" and actor["role"] != "operator":
                    _audit(request, actor, 403)
                    return JSONResponse({"detail": "Journal réservé à l'opérateur"}, status_code=403)
                analytical = path in ("/whatif", "/route-options", "/ai/ask", "/ai/briefing", "/auth/logout")
                if unsafe and actor["role"] == "viewer" and not analytical:
                    _audit(request, actor, 403)
                    return JSONResponse({"detail": "Droits opérateur requis"}, status_code=403)
        request.state.actor = actor
    response = await call_next(request)
    if secure and unsafe:
        _audit(request, getattr(request.state, "actor", actor), response.status_code)
    return response

app.include_router(events_router)
app.include_router(risk_router)
app.include_router(whatif_router)
app.include_router(missions_router)
app.include_router(dispatch_router)
app.include_router(infra_router)
app.include_router(ai_router)
app.include_router(auth_router)
app.include_router(replay_router)
app.include_router(notifications_router)


@app.get("/", tags=["Monitoring"])
def root():
    return {"project": "Urban Butterfly", "status": "running"}


@app.get("/health", tags=["Monitoring"])
def health():
    checks = {}
    ok = True
    for name, verify in (("neo4j", neo4j_client.verify), ("mongodb", mongo_client.verify)):
        try:
            verify()
            checks[name] = "up"
        except Exception as exc:
            ok = False
            checks[name] = f"down ({exc.__class__.__name__})"
    return {"status": "healthy" if ok else "degraded", "services": checks}
