from __future__ import annotations

from pydantic import BaseModel

from app.core.config import get_settings
from app.database import check_database_connection


class DependencyStatus(BaseModel):
    status: str
    type: str | None = None


class DependencyHealthResponse(BaseModel):
    status: str
    environment: str
    service: str
    dependencies: dict[str, DependencyStatus]


def get_backend_dependency_status() -> DependencyStatus:
    return DependencyStatus(status="healthy", type="fastapi")


def get_database_dependency_status() -> DependencyStatus:
    return DependencyStatus(
        status="healthy" if check_database_connection() else "unhealthy",
        type="sqlite",
    )


def get_dependency_health() -> DependencyHealthResponse:
    settings = get_settings()
    backend_status = get_backend_dependency_status()
    database_status = get_database_dependency_status()

    overall_status = "healthy"
    if backend_status.status != "healthy" or database_status.status != "healthy":
        overall_status = "degraded"

    return DependencyHealthResponse(
        status=overall_status,
        environment=settings.app_env,
        service=settings.service_name,
        dependencies={
            "backend": backend_status,
            "database": database_status,
        },
    )
