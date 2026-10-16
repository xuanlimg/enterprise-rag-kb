from contextlib import asynccontextmanager
from pathlib import Path

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.api.v1.router import api_router
from app.core.config import settings
from app.core.logging import configure_logging
from app.db.init_db import init_db

STATIC_DIR = Path(__file__).parent / "static"
logger = structlog.get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用启动时初始化日志和数据库。"""
    configure_logging()
    if settings.auto_create_tables:
        try:
            init_db()
        except Exception as exc:
            # 数据库没启动时仍然允许服务监听，方便先打开前端和 Swagger。
            logger.warning("database_init_failed", error=str(exc))
    yield


app = FastAPI(
    title=settings.app_name,
    version="0.2.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

@app.middleware("http")
async def add_no_store_header(request, call_next):
    """本地开发时禁止缓存前端资源，避免浏览器一直用旧页面。"""
    response = await call_next(request)
    if request.url.path == "/" or request.url.path.startswith("/static"):
        response.headers["Cache-Control"] = "no-store"
    return response


app.include_router(api_router, prefix="/api/v1")


@app.get("/")
def index() -> FileResponse:
    """返回最小前端页面。"""
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/api")
def api_info() -> dict[str, str]:
    """返回 API 基本信息。"""
    return {"name": settings.app_name, "docs": "/docs"}
