"""Vision Detect Core API."""
import asyncio
import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import select, text

from app.api.v1 import (admin, auth, dashboard_analytics, dashboard_catalog, dashboard_sales, dashboard_tenant, public,
                        server, storefront)
from app.core.cache import backend_name
from app.core.config import ROOT_DIR, settings
from app.core.errors import install_error_handlers
from app.core.logging import setup_logging
from app.core.middleware import RequestContextMiddleware
from app.db.session import SessionLocal, engine
from app.services.vision.router import demo_mode, ensure_models

log = logging.getLogger("app")
WIDGET_DIR = ROOT_DIR / "packages" / "widget" / "src"
DEMO_DIR = Path(__file__).parent / "demo"


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging(settings.is_dev)
    async with SessionLocal() as db:
        await db.execute(text("SELECT 1"))
        await ensure_models(db)
    log.info("API ishga tushdi · env=%s · vision=%s · cache=%s", settings.APP_ENV,
             "DEMO (GEMINI_API_KEY yo'q)" if demo_mode() else "gemini", backend_name())
    tasks: list[asyncio.Task] = []
    if settings.RUN_WORKER_IN_API:
        from app.workers import scheduler
        tasks = scheduler.start()
    yield
    for t in tasks:
        t.cancel()
    await engine.dispose()


def create_app() -> FastAPI:
    app = FastAPI(
        title="Vision Detect API", version="2.0.0", lifespan=lifespan,
        docs_url="/docs" if settings.is_dev else None, redoc_url=None,
        openapi_url="/openapi.json" if settings.is_dev else None,
    )
    app.add_middleware(RequestContextMiddleware)
    install_error_handlers(app)

    routers = [public.router, server.router, auth.router, dashboard_analytics.router, dashboard_catalog.router,
               dashboard_tenant.router, dashboard_sales.router, admin.router]
    if not settings.is_basic_edition:      # Basic edition: savdo do'koni (storefront) API'si umuman yo'q
        routers.append(storefront.router)
    for r in routers:
        app.include_router(r)

    @app.get("/healthz", include_in_schema=False)
    async def healthz():
        return {"status": "ok"}

    @app.get("/readyz", include_in_schema=False)
    async def readyz():
        try:
            async with SessionLocal() as db:
                await db.execute(text("SELECT 1"))
        except Exception:
            return JSONResponse({"status": "error", "database": "down"}, status_code=503)
        return {"status": "ok", "database": "ok", "cache": backend_name()}

    app.mount("/media", StaticFiles(directory=settings.media_path), name="media")

    if WIDGET_DIR.exists():
        app.mount("/cdn/v1", StaticFiles(directory=WIDGET_DIR), name="cdn")

    @app.get("/demo/vanilla", response_class=HTMLResponse, include_in_schema=False)
    @app.get("/demo/vanilla/{page}", response_class=HTMLResponse, include_in_schema=False)
    async def demo(page: str = "index"):
        if not settings.is_dev and settings.APP_ENV != "staging":
            return HTMLResponse("Not found", status_code=404)
        from app.models import ApiKey, Tenant
        async with SessionLocal() as db:
            row = (await db.execute(select(ApiKey.public_key).join(Tenant, Tenant.id == ApiKey.tenant_id)
                                    .where(Tenant.slug == "demo-shop", ApiKey.revoked_at.is_(None)).limit(1))).first()
        if not row:
            return HTMLResponse("<h3>Demo do'kon topilmadi. Avval: python scripts/seed_demo.py</h3>", status_code=404)
        name = "thanks.html" if page == "thanks" else "index.html"
        html = (DEMO_DIR / name).read_text(encoding="utf-8")
        return html.replace("{{PK}}", row[0]).replace("{{API}}", settings.PUBLIC_API_URL.rstrip("/"))

    return app


app = create_app()
