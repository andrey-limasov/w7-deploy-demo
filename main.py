import asyncio
import logging
import uuid
from collections.abc import Awaitable, Callable

import psycopg
import structlog
from fastapi import FastAPI, Header, Request, Response
from fastapi.responses import JSONResponse

from settings import settings

structlog.configure(
    processors=[
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso", utc=True),
        structlog.processors.format_exc_info,
        structlog.processors.JSONRenderer(),
    ],
    wrapper_class=structlog.make_filtering_bound_logger(logging.INFO),
)
log = structlog.get_logger()

app = FastAPI(
    title="w7-deploy-demo",
    version="0.2.0",
    docs_url="/docs" if settings.app_env == "dev" else None,
    redoc_url="/redoc" if settings.app_env == "dev" else None,
    openapi_url="/openapi.json" if settings.app_env == "dev" else None,
)


@app.middleware("http")
async def request_context(
    request: Request, call_next: Callable[[Request], Awaitable[Response]]
) -> Response:
    request_id = request.headers.get("x-request-id") or uuid.uuid4().hex
    structlog.contextvars.clear_contextvars()
    structlog.contextvars.bind_contextvars(
        request_id=request_id,
        method=request.method,
        path=request.url.path,
        user=request.headers.get("x-user", "anonymous"),
    )
    try:
        response = await call_next(request)
    except Exception:
        log.exception("request failed")
        response = JSONResponse(
            status_code=500, content={"detail": "Internal Server Error"}
        )
    response.headers["X-Request-ID"] = request_id
    log.info("request finished", status=response.status_code)
    return response


@app.get("/health", response_model=None)
def health() -> dict[str, str] | JSONResponse:
    try:
        with psycopg.connect(settings.database_url, connect_timeout=3) as conn:
            conn.execute("SELECT 1")
    except psycopg.Error as exc:
        log.warning("database unavailable", error=str(exc))
        return JSONResponse(status_code=503, content={"status": "unhealthy"})
    return {"status": "healthy"}


@app.get("/version")
def version() -> dict[str, str]:
    return {"version": app.version}


@app.get("/report")
async def report(x_user: str = Header(default="anonymous")) -> dict[str, str | int]:
    log.info("report: loading data")
    await asyncio.sleep(0.2)
    log.info("report: computing totals")
    await asyncio.sleep(0.2)
    if x_user == "bob":
        raise RuntimeError("totals: division by zero")
    log.info("report: done")
    return {"user": x_user, "total": 42}
