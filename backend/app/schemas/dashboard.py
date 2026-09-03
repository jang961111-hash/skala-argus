"""대시보드 스키마 (CONTRACT §4-4). `role` 은 필수이고 토큰 역할과 다르면 403."""
from __future__ import annotations

from app.schemas.base import CamelModel


class EngineerDashboard(CamelModel):
    """E_01 KPI 4종 — 작성중·진행중(AI)·승인대기·반려보완. **평균 승인 소요시간 없음.**"""

    draft: int
    ai_running: int
    pending: int
    rejected: int


class RejectReason(CamelModel):
    reason: str
    count: int


class SafetyDashboard(CamelModel):
    """S_01 KPI — 승인대기·오늘처리·이번달승인·이번달거절 + 거절 사유 TOP5."""

    pending: int
    today_processed: int
    month_approved: int
    month_rejected: int
    reject_reasons_top: list[RejectReason] = []
