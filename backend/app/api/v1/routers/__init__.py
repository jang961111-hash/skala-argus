"""CONTRACT §4 — API 15개.

`/auth/signup`·`/auth/login` 만 공개고 나머지는 전부 JWT Bearer 가 필요하다.
인증 게이트는 각 라우터의 `Depends(get_current_user | require_engineer | require_safety_manager)`
에 걸려 있다 — 역할별로 다른 의존성을 쓰기 때문에 라우터 단위 일괄 적용은 하지 않는다.
"""
from fastapi import APIRouter

from app.api.v1.routers import agent_runs, approvals, auth, dashboard, work_requests

api_router = APIRouter()
api_router.include_router(auth.router)  # 1 · 2 · 3
api_router.include_router(dashboard.router)  # 4
api_router.include_router(work_requests.router)  # 5 · 6 · 7 · 8 · 9 · 10 · 14
api_router.include_router(agent_runs.router)  # 11 · 12
api_router.include_router(agent_runs.results_router)  # 13
api_router.include_router(approvals.router)  # 15
