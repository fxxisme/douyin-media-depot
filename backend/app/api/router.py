from __future__ import annotations

from fastapi import APIRouter

from app.api.routes import accounts, auth, media, settings, sources, tasks

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(auth.router)
api_router.include_router(accounts.router)
api_router.include_router(sources.router)
api_router.include_router(tasks.router)
api_router.include_router(media.router)
api_router.include_router(settings.router)
