"""Sessions opaques, rôles et journalisation du poste de commandement.

Mode demo : accès local historique. Mode secure : aucune route métier anonyme.
Les secrets restent dans l'environnement ; seuls les empreintes des sessions
sont stockées en base. Ne jamais journaliser le corps des requêtes.
"""

import hashlib
import hmac
import secrets
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Request, Response
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from app.core.config import get_settings
from app.db.mongo_client import mongo_client

router = APIRouter(prefix="/auth", tags=["Sécurité"])
COOKIE = "ub_session"
SESSION_HOURS = 8
ALLOWED_ORIGINS = {"http://localhost:5173", "http://127.0.0.1:5173"}


def _digest(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def validate_config():
    settings = get_settings()
    if settings.security_mode not in ("demo", "secure"):
        raise RuntimeError("SECURITY_MODE doit valoir demo ou secure")
    if settings.security_mode == "secure":
        if len(settings.auth_operator_password) < 14 or len(settings.auth_agency_key) < 32:
            raise RuntimeError("Mode secure : AUTH_OPERATOR_PASSWORD (14 caractères) et AUTH_AGENCY_KEY (32 caractères) requis")
        if settings.auth_viewer_password and len(settings.auth_viewer_password) < 14:
            raise RuntimeError("AUTH_VIEWER_PASSWORD doit contenir au moins 14 caractères")
        if getattr(settings, "neo4j_password", None) == "urbanbutterfly" or \
                "admin:urbanbutterfly@" in getattr(settings, "mongo_uri", ""):
            raise RuntimeError("Mode secure : changer les identifiants par défaut des bases")
        if any(origin.startswith("https://") for origin in allowed_origins()) and not settings.auth_cookie_secure:
            raise RuntimeError("Mode secure HTTPS : AUTH_COOKIE_SECURE=true requis")


def allowed_origins() -> set[str]:
    extra = getattr(get_settings(), "auth_allowed_origins", "")
    return ALLOWED_ORIGINS | {origin.strip().rstrip("/") for origin in extra.split(",") if origin.strip()}


def current_actor(request: Request) -> dict | None:
    token = request.cookies.get(COOKIE)
    if not token:
        return None
    session = mongo_client._db.sessions.find_one({"_id": _digest(token),
        "expires_at": {"$gt": datetime.now(timezone.utc)}})
    if not session:
        return None
    return {"name": session["name"], "role": session["role"]}


def _check_password(supplied: str, expected: str, name: str) -> bool:
    # Coût fixe même pour un identifiant inconnu ; aucune comparaison plaintext.
    salt = hashlib.sha256(("urban-butterfly:" + name).encode()).digest()
    a = hashlib.pbkdf2_hmac("sha256", supplied.encode(), salt, 180_000)
    b = hashlib.pbkdf2_hmac("sha256", expected.encode(), salt, 180_000)
    return hmac.compare_digest(a, b)


class Login(BaseModel):
    username: str = Field(min_length=1, max_length=64)
    password: str = Field(min_length=1, max_length=512)


@router.get("/config")
def config():
    return {"secure": get_settings().security_mode == "secure"}


@router.post("/login")
def login(credentials: Login, request: Request, response: Response):
    settings = get_settings()
    if settings.security_mode != "secure":
        return JSONResponse({"detail": "Connexion inutile en mode démonstration"}, status_code=400)
    name = credentials.username.strip().lower()
    # Limitation par IP + identifiant. Ne dépend pas d'en-têtes IP non fiables.
    key = _digest(f"{request.client.host if request.client else 'unknown'}:{name}")
    now = datetime.now(timezone.utc)
    attempts = mongo_client._db.login_attempts.find_one({"_id": key})
    if attempts and attempts.get("until", now) > now and attempts.get("count", 0) >= 5:
        return JSONResponse({"detail": "Trop de tentatives. Réessayez dans cinq minutes."}, status_code=429)
    passwords = {"operateur": (settings.auth_operator_password, "operator")}
    if settings.auth_viewer_password:
        passwords["observateur"] = (settings.auth_viewer_password, "viewer")
    expected, role = passwords.get(name, (settings.auth_operator_password, None))
    valid = _check_password(credentials.password, expected, name)
    if role is None or not valid:
        if not attempts or attempts.get("until", now) <= now:
            mongo_client._db.login_attempts.update_one({"_id": key},
                {"$set": {"count": 1, "until": now + timedelta(minutes=5)}}, upsert=True)
        else:
            mongo_client._db.login_attempts.update_one({"_id": key}, {"$inc": {"count": 1}})
        return JSONResponse({"detail": "Identifiants incorrects"}, status_code=401)
    mongo_client._db.login_attempts.delete_one({"_id": key})
    token = secrets.token_urlsafe(48)
    mongo_client._db.sessions.insert_one({"_id": _digest(token), "name": name,
        "role": role, "expires_at": now + timedelta(hours=SESSION_HOURS)})
    request.state.actor = {"name": name, "role": role}
    response.set_cookie(COOKIE, token, max_age=SESSION_HOURS * 3600, httponly=True,
                        secure=settings.auth_cookie_secure, samesite="strict", path="/")
    return {"name": name, "role": role}


@router.get("/me")
def me(request: Request):
    return getattr(request.state, "actor", None) or {"name": "demo", "role": "operator"}


@router.get("/audit")
def audit(limit: int = 20):
    if get_settings().security_mode != "secure":
        return []
    return list(mongo_client._db.audit_log.find({}, {"_id": 0})
                .sort("at", -1).limit(max(1, min(limit, 100))))


@router.post("/logout")
def logout(request: Request, response: Response):
    token = request.cookies.get(COOKIE)
    if token:
        mongo_client._db.sessions.delete_one({"_id": _digest(token)})
    response.delete_cookie(COOKIE, path="/")
    return {"status": "deconnecte"}
