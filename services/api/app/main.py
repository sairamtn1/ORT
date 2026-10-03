from contextlib import asynccontextmanager
import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError
from .api.v1.auth import router as auth_router
from .api.v1.crud import router as crud_router
from .api.v1.health import router as health_router
from .api.v1.operations import router as operations_router
from .config import get_settings
from .db import engine
from .errors import AppError, app_error_handler, integrity_error_handler, validation_error_handler
from .logging_config import configure_logging
from .middleware import RequestContextMiddleware

settings = get_settings()
configure_logging(settings.log_level)
logger = logging.getLogger("parken.application")


@asynccontextmanager
async def lifespan(_: FastAPI):
    logger.info("starting %s", settings.app_name, extra={"request_id": "-"})
    yield
    await engine.dispose()
    logger.info("stopped %s", settings.app_name, extra={"request_id": "-"})


async def _unexpected_error_handler(request, exc: Exception) -> JSONResponse:
    request_id = getattr(request.state, "request_id", None)
    logger.exception("unhandled_error", extra={"request_id": request_id or "-"})
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error", "request_id": request_id},
    )


app = FastAPI(
    title="ORT API",
    version="1.0.0",
    description="Parking discovery, inventory, booking, payment, review, and notification API.",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
    lifespan=lifespan,
)

app.add_middleware(RequestContextMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_exception_handler(AppError, app_error_handler)
app.add_exception_handler(500, _unexpected_error_handler)  # type: ignore[arg-type]
app.add_exception_handler(422, validation_error_handler)  # type: ignore[arg-type]
app.add_exception_handler(IntegrityError, integrity_error_handler)
app.include_router(health_router, prefix=settings.api_prefix)
app.include_router(auth_router, prefix=settings.api_prefix)
app.include_router(crud_router, prefix=settings.api_prefix)
app.include_router(operations_router, prefix=settings.api_prefix)


@app.get("/api/healthz", tags=["health"])
async def healthz() -> JSONResponse:
    return JSONResponse({"status": "ok"})