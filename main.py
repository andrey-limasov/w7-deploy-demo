import asyncio
import logging

import psycopg
from fastapi import FastAPI, Header
from fastapi.responses import JSONResponse

from settings import settings

app = FastAPI(
    title="w7-deploy-demo",
    version="0.1.0",
    docs_url="/docs" if settings.app_env == "dev" else None,
    redoc_url="/redoc" if settings.app_env == "dev" else None,
    openapi_url="/openapi.json" if settings.app_env == "dev" else None,
)
logger = logging.getLogger("uvicorn.error")


@app.get("/health", response_model=None)
def health() -> dict[str, str] | JSONResponse:
    try:
        with psycopg.connect(settings.database_url, connect_timeout=3) as conn:
            conn.execute("SELECT 1")
    except psycopg.Error as exc:
        logger.warning("Health check: database is unavailable: %s", exc)
        return JSONResponse(status_code=503, content={"status": "unhealthy"})
    return {"status": "healthy"}


@app.get("/version")
def version() -> dict[str, str]:
    return {"version": app.version}


@app.get("/report")
async def report(x_user: str = Header(default="anonymous")) -> dict[str, str | int]:
    logger.info("report: loading data")
    await asyncio.sleep(0.2)
    logger.info("report: computing totals")
    await asyncio.sleep(0.2)
    if x_user == "bob":
        raise RuntimeError("totals: division by zero")
    logger.info("report: done")
    return {"user": x_user, "total": 42}
