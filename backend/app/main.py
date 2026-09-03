from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.v1.routers import api_router
from app.core.config import get_settings
from app.db.session import Base, SessionLocal, engine
from app.seed import seed_if_empty
from app.services.errors import ServiceError

import app.models  # noqa: F401  — register all tables on Base.metadata

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("replaceflow")
settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings.validate_egress()
    Base.metadata.create_all(bind=engine)
    if settings.seed_on_startup:
        db = SessionLocal()
        try:
            if seed_if_empty(db):
                log.info("seeded sample data from docs/CONTRACT.md")
        finally:
            db.close()
    log.info("AI_PROVIDER=%s EGRESS_ALLOWED=%s DB=%s", settings.ai_provider, settings.egress_allowed, settings.database_url)
    yield


app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    description="ReplaceFlow — 반도체 설비 부품 교체 승인 프로세스 에이전트 API (docs/CONTRACT.md)",
    lifespan=lifespan,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(api_router, prefix=settings.api_prefix)


@app.exception_handler(ServiceError)
async def service_error_handler(_: Request, exc: ServiceError):
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})


@app.get("/health", tags=["health"])
def health():
    return {"status": "ok", "ai_provider": settings.ai_provider, "egress_allowed": settings.egress_allowed}
