from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.db.mongo_client import mongo_client
from app.db.neo4j_client import neo4j_client
from app.routes.events import router as events_router
from app.routes.infra import router as infra_router
from app.routes.risk import router as risk_router
from app.routes.whatif import router as whatif_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
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
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(events_router)
app.include_router(risk_router)
app.include_router(whatif_router)
app.include_router(infra_router)


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
