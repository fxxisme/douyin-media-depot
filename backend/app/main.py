from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from app.api.router import api_router
from app.core.config import settings
from app.core.paths import ensure_storage_dirs
from app.core.responses import fail
from app.db.init_db import init_db


def create_app() -> FastAPI:
    settings.validate_required()
    ensure_storage_dirs()
    init_db()

    app = FastAPI(title=settings.app_name)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=list(settings.cors_origins),
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(api_router)

    static_dir = Path(__file__).resolve().parents[2] / "static"
    if static_dir.exists():
        app.mount("/assets", StaticFiles(directory=static_dir / "assets"), name="assets")

        @app.get("/{full_path:path}", include_in_schema=False)
        def spa_fallback(full_path: str):
            target = static_dir / full_path
            if full_path and target.exists() and target.is_file():
                return FileResponse(target)
            return FileResponse(static_dir / "index.html")

    return app


app = create_app()


@app.exception_handler(HTTPException)
async def http_exception_handler(_request: Request, exc: HTTPException):
    code = "http_error"
    if exc.status_code == 401:
        code = "unauthorized"
    elif exc.status_code == 404:
        code = "not_found"
    return JSONResponse(status_code=exc.status_code, content=fail(code, str(exc.detail)))


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(_request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=422,
        content=fail("validation_error", "请求参数不合法", {"errors": exc.errors()}),
    )
