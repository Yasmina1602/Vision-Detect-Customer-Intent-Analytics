"""request-id, kirish logi, CORS (vidjet uchun dinamik, dashboard uchun allowlist), xavfsizlik sarlavhalari."""
import logging
import time
import uuid

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.core.config import settings

log = logging.getLogger("app.http")

PUBLIC_PREFIXES = ("/v1/public/", "/cdn/")
ALLOW_HEADERS = "Content-Type, Authorization, X-Vision-Key, X-Tenant-Id, X-Request-Id"


class RequestContextMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        rid = request.headers.get("x-request-id") or uuid.uuid4().hex[:16]
        request.state.request_id = rid
        origin = request.headers.get("origin")
        path = request.url.path
        is_public = path.startswith(PUBLIC_PREFIXES)
        dashboard_ok = bool(origin) and origin in settings.cors_origins

        if request.method == "OPTIONS" and origin and (is_public or dashboard_ok):
            resp = Response(status_code=204)
        else:
            started = time.perf_counter()
            resp = await call_next(request)
            ms = int((time.perf_counter() - started) * 1000)
            if not path.startswith(("/cdn/", "/healthz")):
                log.info("%s %s %s %sms", request.method, path, resp.status_code, ms,
                         extra={"request_id": rid, "path": path, "status": resp.status_code, "duration_ms": ms,
                                "tenant_id": getattr(request.state, "tenant_id", None)})

        if origin and is_public:
            # Kalit bo'yicha domen tekshiruvi dependency ichida (403). Bu yerda faqat brauzer CORS.
            resp.headers["Access-Control-Allow-Origin"] = origin
            resp.headers["Vary"] = "Origin"
            resp.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
            resp.headers["Access-Control-Allow-Headers"] = ALLOW_HEADERS
            resp.headers["Access-Control-Max-Age"] = "600"
        elif dashboard_ok:
            resp.headers["Access-Control-Allow-Origin"] = origin  # type: ignore[assignment]
            resp.headers["Access-Control-Allow-Credentials"] = "true"
            resp.headers["Vary"] = "Origin"
            resp.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, PATCH, DELETE, OPTIONS"
            resp.headers["Access-Control-Allow-Headers"] = ALLOW_HEADERS

        if path.startswith("/cdn/"):
            resp.headers["Cache-Control"] = "public, max-age=300"   # loader qisqa TTL
        resp.headers["X-Request-Id"] = rid
        resp.headers["X-Content-Type-Options"] = "nosniff"
        resp.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        if not settings.is_dev:
            resp.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        return resp
