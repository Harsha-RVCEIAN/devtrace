
"""
DevTrace FastAPI application entry point.

This module constructs the central FastAPI application, registers the API
routers, and exposes the initial health-check endpoint.

Responsibilities:
    1. Load application metadata and runtime settings from shared configuration.
    2. Construct the central FastAPI application instance.
    3. Register user, project, and AI-interaction API routers.
    4. Expose GET /health to confirm that the API process is responding.

The health endpoint checks the API process only; it does not verify PostgreSQL
connectivity. Database connectivity is managed separately by the database layer.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.routing import _IncludedRouter
from starlette.routing import BaseRoute

# Shared application configuration.
from app.core.config import settings

# API routers.
# Each router defines its own endpoint paths, request validation,
# response schemas, and HTTP error handling.
from app.api.routes import (
    alternatives,
    code_changes,
    commits,
    decisions,
    evidence,
    interactions,
    nlp,
    projects,
    users,
)


class DevTraceFastAPI(FastAPI):
    """
    FastAPI application with route inspection support.

    In FastAPI versions that store included routers as _IncludedRouter
    objects, this property exposes the underlying routes for inspection.

    This is intended for development and diagnostic scripts. Normal HTTP
    request dispatch and OpenAPI generation remain managed by FastAPI.
    """

    @property
    def routes(self) -> list[BaseRoute]:
        """
        Return application routes, expanding included routers for inspection.

        Returns:
            list[BaseRoute]: Direct routes and routes from included routers.

        Note:
            _IncludedRouter is a private FastAPI implementation detail.
            This compatibility helper may need adjustment after a FastAPI
            upgrade. Keep FastAPI dependencies version-controlled.
        """
        flat: list[BaseRoute] = []

        for route in self.router.routes:
            if isinstance(route, _IncludedRouter):
                # Expand the included router so route-inspection scripts can
                # see its endpoint definitions directly.
                flat.extend(route.original_router.routes)
            else:
                flat.append(route)

        return flat


# ---------------------------------------------------------------------------
# Application construction
# ---------------------------------------------------------------------------
# Create the application before registering any API routers.
# The ASGI server imports this object to serve incoming HTTP requests.
app = DevTraceFastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description=(
        "DevTrace tracks software development provenance, including "
        "AI interactions, engineering decisions, evidence, Git commits, "
        "and associated code changes."
    ),
    debug=settings.debug,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)



# ---------------------------------------------------------------------------
# API router registration
# ---------------------------------------------------------------------------
# User endpoints:
#   POST /users
#
# Project endpoints:
#   POST /projects
#   GET  /projects
#   GET  /projects/{project_id}
#   PATCH /projects/{project_id}
#
# AI-interaction endpoints:
#   POST /interactions
#
# Exact paths and supported methods are defined in the individual routers.
app.include_router(users.router)
app.include_router(projects.router)
app.include_router(interactions.router)
app.include_router(decisions.router)
app.include_router(alternatives.router)
app.include_router(evidence.router)
app.include_router(commits.router)
app.include_router(code_changes.router)
app.include_router(nlp.router)

# ---------------------------------------------------------------------------
# Health-check endpoint
# ---------------------------------------------------------------------------
@app.get(
    "/health",
    tags=["Health"],
    summary="Check API process health",
    response_description="Current API process status",
)
def health_check() -> dict[str, str]:
    """
    Return the basic health status of the API process.

    This endpoint intentionally does not open a database session. A successful
    response confirms that the FastAPI application is responding, but does not
    guarantee that PostgreSQL is reachable.

    Returns:
        dict[str, str]: Service status, application name, and environment.
    """
    return {
        "status": "ok",
        "service": settings.app_name,
        "environment": settings.environment,
    }
