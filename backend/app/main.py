from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.responses import JSONResponse

from app.api.projects import router as project_router
from app.core.config import get_settings
from app.database import init_db
from app.services.health_service import DependencyHealthResponse, get_dependency_health
from app.services.project import ProjectNotFoundError


class HealthResponse(BaseModel):
    status: str
    service: str


def build_error_payload(code: str, message: str, details: Any | None = None) -> dict[str, Any]:
    payload: dict[str, Any] = {"error": {"code": code, "message": message}}
    if details is not None:
        payload["error"]["details"] = details
    return payload


settings = get_settings()

app = FastAPI(title=settings.app_name, debug=settings.debug, version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r"https?://(localhost|127\.0\.0\.1):517\d+",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(project_router, prefix=settings.api_prefix)


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    message = exc.detail if isinstance(exc.detail, str) else "Request failed."
    return JSONResponse(
        status_code=exc.status_code,
        content=build_error_payload("HTTP_ERROR", message),
    )


@app.exception_handler(ProjectNotFoundError)
async def project_not_found_exception_handler(request: Request, exc: ProjectNotFoundError) -> JSONResponse:
    return JSONResponse(
        status_code=404,
        content=build_error_payload("PROJECT_NOT_FOUND", str(exc)),
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    details: list[dict[str, str]] = []
    for error in exc.errors():
        location = " -> ".join(str(item) for item in error.get("loc", []))
        details.append({
            "field": location,
            "message": error.get("msg", "Invalid request."),
        })
    return JSONResponse(
        status_code=422,
        content=build_error_payload("VALIDATION_ERROR", "Request validation failed.", details),
    )


@app.middleware("http")
async def error_middleware(request: Request, call_next):
    try:
        return await call_next(request)
    except Exception:
        return JSONResponse(
            status_code=500,
            content=build_error_payload("INTERNAL_SERVER_ERROR", "An unexpected server error occurred."),
        )


@app.on_event("startup")
def startup_event() -> None:
    init_db()


@app.get("/")
def read_root() -> dict[str, str]:
    return {"message": "CodePilot backend is running"}


@app.get(f"{settings.api_prefix}/health", response_model=HealthResponse)
def get_health() -> HealthResponse:
    return HealthResponse(status="ok", service=settings.service_name)


@app.get(f"{settings.api_prefix}/health/dependencies", response_model=DependencyHealthResponse)
def get_dependency_status() -> DependencyHealthResponse:
    return get_dependency_health()
