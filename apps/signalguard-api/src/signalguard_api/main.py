"""FastAPI app factory.

The factory pattern keeps the app construction overridable from tests so a
test client can inject scratch settings (e.g. a tmp_path DB) without
mutating the global lru_cache on ``get_settings``.
"""

from __future__ import annotations

from importlib.metadata import PackageNotFoundError, version

from fastapi import FastAPI, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from starlette.exceptions import HTTPException as StarletteHTTPException

from signalguard_api.config import Settings, get_settings
from signalguard_api.correlation import CorrelationIdMiddleware
from signalguard_api.errors import (
    APIProblem,
    api_problem_handler,
    http_exception_handler,
    starlette_exception_handler,
    unhandled_exception_handler,
    validation_exception_handler,
)
from signalguard_api.lifespan import lifespan
from signalguard_api.routers import (
    anomaly,
    anomaly_actions,
    audit,
    coverage,
    findings,
    health,
    models,
    narratives,
    signins,
    tenants,
    whoami,
)

OPENAPI_TAGS: list[dict[str, str]] = [
    {"name": "health", "description": "Liveness and readiness probes."},
    {"name": "tenants", "description": "Registered tenant inventory."},
    {"name": "findings", "description": "Audit and anomaly findings."},
    {"name": "anomaly", "description": "Per-signin anomaly scores and alerts."},
    {"name": "coverage", "description": "User-app coverage matrix snapshot."},
    {"name": "signins", "description": "Sign-in stats and per-user history."},
    {"name": "audit", "description": "Trigger audit runs and dry runs."},
    {"name": "models", "description": "MLflow model registry view."},
    {"name": "narratives", "description": "LLM-generated finding narratives."},
]


def _resolve_version() -> str:
    try:
        return version("signalguard-api")
    except PackageNotFoundError:
        return "0.0.0"


def create_app(settings: Settings | None = None) -> FastAPI:
    resolved = settings if settings is not None else get_settings()
    app = FastAPI(
        title="signalguard-api",
        version=_resolve_version(),
        description=(
            "HTTP surface over the cstack signalguard data and audit packages. "
            "See /docs for OpenAPI 3.1 and /redoc for the rendered spec."
        ),
        openapi_tags=OPENAPI_TAGS,
        lifespan=lifespan,
        contact={"name": "cstack maintainers", "email": "leunis@vanlabs.dev"},
        license_info={"name": "MIT"},
    )
    app.state.settings = resolved
    app.add_middleware(
        CORSMiddleware,
        allow_origins=resolved.cors_allowed_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_middleware(CorrelationIdMiddleware)
    app.add_exception_handler(HTTPException, http_exception_handler)
    app.add_exception_handler(StarletteHTTPException, starlette_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(APIProblem, api_problem_handler)
    app.add_exception_handler(Exception, unhandled_exception_handler)
    app.include_router(health.router)
    app.include_router(whoami.router)
    app.include_router(tenants.router)
    app.include_router(findings.router)
    app.include_router(anomaly.router)
    app.include_router(coverage.router)
    app.include_router(signins.stats_router)
    app.include_router(signins.user_router)
    app.include_router(audit.router)
    app.include_router(anomaly_actions.router)
    app.include_router(models.router)
    app.include_router(narratives.router)
    return app
