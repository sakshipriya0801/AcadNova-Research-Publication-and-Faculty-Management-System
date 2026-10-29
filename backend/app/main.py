"""Application entry point.

Wires together the FastAPI app, the MongoDB connection lifecycle, and the
health endpoint.  Business logic, routes and integrations are intentionally
kept out of this module.
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pymongo.errors import ConfigurationError, ConnectionFailure

from app.config.settings import get_settings
from app.database import mongodb
from app.routes import (
    academic_years,
    auth,
    departments,
    documents,
    faculty,
    orcid,
    points,
    publications,
    rag,
    research_search,
    scopus,
    web_of_science,
)
from app.routes.admin import (
    academic_years as admin_academic_years,
    accounts as admin_accounts,
    audit_logs as admin_audit_logs,
    departments as admin_departments,
    eligibility as admin_eligibility,
    faculty as admin_faculty,
    invitations as admin_invitations,
    publications as admin_publications,
    rules as admin_rules,
    summary as admin_summary,
)
from app.schemas.health import HealthResponse

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialise MongoDB on startup and cleanly close it on shutdown."""
    mongodb.init_mongodb()
    try:
        mongodb.create_indexes()
        from app.services import user_service

        user_service.reconcile_approval_statuses()
    except Exception as exc:  # defensive: index creation must not block startup
        logger.warning("Index creation skipped: %s", exc)
    yield
    mongodb.close_mongodb()


app = FastAPI(
    title="AcadNova — A New Era of Research",
    description=(
        "AcadNova: an academic research and faculty performance platform with "
        "publication verification, performance analytics and an AI Research Assistant."
    ),
    version="0.1.0",
    lifespan=lifespan,
)

# Browser clients may run on a different origin than the API (e.g. the Vite
# dev server during development).  Origins are configuration-driven; the
# wildcard is only honoured when explicitly configured, in which case
# credentialed requests are disabled because the two are incompatible.
_cors_origins = [
    origin.strip()
    for origin in get_settings().cors_origins.split(",")
    if origin.strip()
]
_allow_all_origins = "*" in _cors_origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if _allow_all_origins else _cors_origins,
    allow_credentials=not _allow_all_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(academic_years.router)
app.include_router(departments.router)
app.include_router(faculty.router)
app.include_router(publications.router)
app.include_router(documents.router)
app.include_router(points.router)
app.include_router(orcid.router)
app.include_router(scopus.router)
app.include_router(web_of_science.router)
app.include_router(rag.router)
app.include_router(research_search.router)

app.include_router(admin_academic_years.router)
app.include_router(admin_departments.router)
app.include_router(admin_faculty.router)
app.include_router(admin_rules.router)
app.include_router(admin_eligibility.router)
app.include_router(admin_summary.router)
app.include_router(admin_publications.router)
app.include_router(admin_audit_logs.router)
app.include_router(admin_accounts.router)
app.include_router(admin_invitations.router)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    """Return clean 400 responses for invalid request data (no stack traces)."""
    errors: list[str] = []
    for err in exc.errors():
        loc = ".".join(str(part) for part in err.get("loc", []) if part != "body")
        msg = err.get("msg", "Invalid value")
        errors.append(f"{loc}: {msg}" if loc else msg)
    return JSONResponse(status_code=400, content={"detail": errors})


@app.exception_handler(ConnectionFailure)
async def mongo_connection_failure_handler(
    request: Request, exc: ConnectionFailure
) -> JSONResponse:
    """Return a clean 503 when MongoDB is unreachable (instead of a 500 traceback)."""
    logger.exception("MongoDB connection failure during request")
    return JSONResponse(
        status_code=503,
        content={"detail": "Database connection failed. Please try again later."},
    )


@app.exception_handler(ConfigurationError)
async def mongo_configuration_error_handler(
    request: Request, exc: ConfigurationError
) -> JSONResponse:
    """Return a clean 503 for an invalid MongoDB configuration (no internals)."""
    logger.exception("MongoDB configuration error during request")
    return JSONResponse(
        status_code=503,
        content={"detail": "Database configuration error. Please try again later."},
    )


@app.get("/api/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """Report API and MongoDB status without exposing credentials."""
    if mongodb.check_database_connection():
        return HealthResponse(status="ok", database="connected")
    return HealthResponse(status="degraded", database="disconnected")
