from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.api.v1.routers import api_router
from app.core.config import DEV_SECRET_KEY, get_settings
from app.core.errors import CODE_BY_STATUS, AppError, ErrorCode
from app.db.session import Base, SessionLocal, engine
from app.seed import seed_if_empty

import app.models  # noqa: F401  — register all tables on Base.metadata

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("argus")
settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings.validate_egress()
    if settings.secret_key == DEV_SECRET_KEY:
        log.warning("SECRET_KEY is the built-in dev value — set SECRET_KEY in backend/.env before any real deployment")
    settings.uploads_dir.mkdir(parents=True, exist_ok=True)
    Base.metadata.create_all(bind=engine)
    if settings.seed_on_startup:
        db = SessionLocal()
        try:
            if seed_if_empty(db):
                log.info("seeded sample data (docs/CONTRACT.md)")
        finally:
            db.close()
    log.info("AI_PROVIDER=%s EGRESS_ALLOWED=%s DB=%s", settings.ai_provider, settings.egress_allowed, settings.database_url)
    yield


app = FastAPI(
    title=settings.app_name,
    version="3.0.0",
    description="부품 교체 요청·승인 시스템 (REQ-F-0001) — docs/CONTRACT.md v3.0",
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

# 업로드된 사진 서빙. 계약의 API 15개에는 이미지를 내려받을 경로가 없는데 S_02 는 사진을
# 띄워야 하므로 정적 마운트로 메운다. photos 응답의 originalUrl·thumbnailUrl 이 이 경로다.
settings.uploads_dir.mkdir(parents=True, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=settings.uploads_dir), name="uploads")


# ------------------------------------------------------------ 단일 에러 포맷
# CONTRACT §1.1: 모든 4xx·5xx 는 {code, message, fieldErrors?} 다.
# FastAPI 기본 {"detail": ...} 이 밖으로 나가지 않도록 세 종류를 전부 가로챈다.
@app.exception_handler(AppError)
async def app_error_handler(_: Request, exc: AppError):
    return JSONResponse(status_code=exc.status_code, content=exc.to_payload())


@app.exception_handler(RequestValidationError)
async def validation_error_handler(_: Request, exc: RequestValidationError):
    """Pydantic 검증 실패 → 400 VALIDATION_FAILED + fieldErrors.

    계약의 유일한 422 는 SUBMIT_REQUIRED_FIELD_MISSING 이므로 FastAPI 기본 422 를 쓰지 않는다.
    """
    field_errors = []
    for error in exc.errors():
        location = [str(part) for part in error.get("loc", []) if part not in ("body", "query", "path", "header")]
        field_errors.append({"field": ".".join(location) or "body", "message": error.get("msg", "invalid")})
    return JSONResponse(
        status_code=400,
        content=jsonable_encoder(
            {"code": ErrorCode.VALIDATION_FAILED.value, "message": "입력값이 올바르지 않습니다", "fieldErrors": field_errors}
        ),
    )


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(_: Request, exc: StarletteHTTPException):
    code = CODE_BY_STATUS.get(exc.status_code, ErrorCode.INTERNAL_ERROR)
    return JSONResponse(status_code=exc.status_code, content={"code": code.value, "message": str(exc.detail)})


@app.exception_handler(Exception)
async def unhandled_error_handler(_: Request, exc: Exception):
    log.exception("unhandled error")
    return JSONResponse(
        status_code=500,
        content={"code": ErrorCode.INTERNAL_ERROR.value, "message": "서버 내부 오류가 발생했습니다"},
    )


@app.get("/health", tags=["health"])
def health():
    return {"status": "ok", "aiProvider": settings.ai_provider, "egressAllowed": settings.egress_allowed}
