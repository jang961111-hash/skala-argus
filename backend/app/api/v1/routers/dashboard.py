from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.models import User
from app.schemas.base import ErrorResponse
from app.schemas.dashboard import EngineerDashboard, SafetyDashboard
from app.services.dashboard_service import DashboardService

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get(
    "/summary",
    response_model=EngineerDashboard | SafetyDashboard,
    responses={code: {"model": ErrorResponse} for code in (400, 401, 403)},
    summary="역할별 KPI — role 필수, 토큰 역할과 다르면 403",
)
def dashboard_summary(
    role: Literal["engineer", "safety"] = Query(..., description="토큰 역할과 일치해야 한다"),
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
):
    return DashboardService(db).summary(role, current)
