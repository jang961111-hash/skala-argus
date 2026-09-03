from fastapi import APIRouter

from app.api.v1.routers import agent_runs, dashboard, documents, laws, master, tenants, work_requests

api_router = APIRouter()
api_router.include_router(work_requests.router)
api_router.include_router(agent_runs.router)
api_router.include_router(documents.router)
api_router.include_router(master.router)
api_router.include_router(laws.router)
api_router.include_router(dashboard.router)
api_router.include_router(tenants.router)
