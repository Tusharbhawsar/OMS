from fastapi import APIRouter

from app.api.v1.endpoints import dashboard, health, notifications, outages, uploads

api_router = APIRouter()
api_router.include_router(health.router, tags=["System"],include_in_schema=True)
api_router.include_router(uploads.router, prefix="/uploads", tags=["Uploads"])
api_router.include_router(outages.router, prefix="/outages", tags=["Outages"],include_in_schema=True)
api_router.include_router(notifications.router, prefix="/notifications", tags=["Notifications"],include_in_schema=True)
api_router.include_router(dashboard.router, prefix="/dashboard", tags=["Dashboard"],include_in_schema=True)