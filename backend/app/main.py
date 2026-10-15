from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.responses import JSONResponse

from app.api.architectures import router as architecture_router
from app.api.llm import router as llm_router
from app.api.projects import router as project_router
from app.api.requirements import router as requirement_router
from app.api.tasks import router as task_router
from app.core.config import get_settings
from app.database import init_db
from app.services.architecture import (
    ArchitectureAlreadyExistsError,
    ArchitectureNotFoundError,
    ArchitectureProjectMismatchError,
)
from app.services.health_service import DependencyHealthResponse, get_dependency_health
from app.services.project import ProjectNotFoundError
from app.services.requirement import (
    CrossProjectAssociationError,
    RequirementNotFoundError,
    RequirementProjectMismatchError,
    RequirementTaskAlreadyLinkedError,
    RequirementTaskNotLinkedError,
)
from app.schemas.llm import LLMError
from app.schemas.requirement_generation import (
    GenerationSchemaValidationError,
    ProposalLifecycleError,
)
from app.services.project_context_builder import CrossProjectContextError
from app.services.task import TaskNotFoundError, TaskProjectMismatchError


class HealthResponse(BaseModel):
    status: str
    service: str


def build_error_payload(code: str, message: str, details: Any | None = None) -> dict[str, Any]:
    payload: dict[str, Any] = {"error": {"code": code, "message": message}}
    if details is not None:
        payload["error"]["details"] = details
    return payload


settings = get_settings()

app = FastAPI(title=settings.app_name, debug=settings.debug, version='0.1.0')

app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r"https?://(localhost|127\.0\.0\.1):517\d+",
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*'],
)

app.include_router(project_router, prefix=settings.api_prefix)
app.include_router(requirement_router, prefix=settings.api_prefix)
app.include_router(architecture_router, prefix=settings.api_prefix)
app.include_router(task_router, prefix=settings.api_prefix)
app.include_router(llm_router, prefix=settings.api_prefix)


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    message = exc.detail if isinstance(exc.detail, str) else 'Request failed.'
    return JSONResponse(
        status_code=exc.status_code,
        content=build_error_payload('HTTP_ERROR', message),
    )


@app.exception_handler(ProjectNotFoundError)
async def project_not_found_exception_handler(request: Request, exc: ProjectNotFoundError) -> JSONResponse:
    return JSONResponse(
        status_code=404,
        content=build_error_payload('PROJECT_NOT_FOUND', str(exc)),
    )


@app.exception_handler(RequirementNotFoundError)
async def requirement_not_found_exception_handler(request: Request, exc: RequirementNotFoundError) -> JSONResponse:
    return JSONResponse(
        status_code=404,
        content=build_error_payload('REQUIREMENT_NOT_FOUND', str(exc)),
    )


@app.exception_handler(RequirementProjectMismatchError)
async def requirement_project_mismatch_exception_handler(request: Request, exc: RequirementProjectMismatchError) -> JSONResponse:
    return JSONResponse(
        status_code=404,
        content=build_error_payload('REQUIREMENT_PROJECT_MISMATCH', str(exc)),
    )


@app.exception_handler(ArchitectureNotFoundError)
async def architecture_not_found_exception_handler(request: Request, exc: ArchitectureNotFoundError) -> JSONResponse:
    return JSONResponse(
        status_code=404,
        content=build_error_payload('ARCHITECTURE_NOT_FOUND', str(exc)),
    )


@app.exception_handler(ArchitectureAlreadyExistsError)
async def architecture_already_exists_exception_handler(request: Request, exc: ArchitectureAlreadyExistsError) -> JSONResponse:
    return JSONResponse(
        status_code=409,
        content=build_error_payload('ARCHITECTURE_ALREADY_EXISTS', str(exc)),
    )


@app.exception_handler(ArchitectureProjectMismatchError)
async def architecture_project_mismatch_exception_handler(request: Request, exc: ArchitectureProjectMismatchError) -> JSONResponse:
    return JSONResponse(
        status_code=404,
        content=build_error_payload('ARCHITECTURE_PROJECT_MISMATCH', str(exc)),
    )


@app.exception_handler(TaskNotFoundError)
async def task_not_found_exception_handler(request: Request, exc: TaskNotFoundError) -> JSONResponse:
    return JSONResponse(
        status_code=404,
        content=build_error_payload('TASK_NOT_FOUND', str(exc)),
    )


@app.exception_handler(TaskProjectMismatchError)
async def task_project_mismatch_exception_handler(request: Request, exc: TaskProjectMismatchError) -> JSONResponse:
    return JSONResponse(
        status_code=404,
        content=build_error_payload('TASK_PROJECT_MISMATCH', str(exc)),
    )


@app.exception_handler(CrossProjectAssociationError)
async def cross_project_association_exception_handler(request: Request, exc: CrossProjectAssociationError) -> JSONResponse:
    return JSONResponse(
        status_code=400,
        content=build_error_payload('CROSS_PROJECT_ASSOCIATION', str(exc)),
    )


@app.exception_handler(RequirementTaskAlreadyLinkedError)
async def requirement_task_already_linked_exception_handler(request: Request, exc: RequirementTaskAlreadyLinkedError) -> JSONResponse:
    return JSONResponse(
        status_code=409,
        content=build_error_payload('REQUIREMENT_TASK_ALREADY_LINKED', str(exc)),
    )


@app.exception_handler(RequirementTaskNotLinkedError)
async def requirement_task_not_linked_exception_handler(request: Request, exc: RequirementTaskNotLinkedError) -> JSONResponse:
    return JSONResponse(
        status_code=404,
        content=build_error_payload('REQUIREMENT_TASK_NOT_LINKED', str(exc)),
    )


@app.exception_handler(CrossProjectContextError)
async def cross_project_context_exception_handler(request: Request, exc: CrossProjectContextError) -> JSONResponse:
    return JSONResponse(
        status_code=400,
        content=build_error_payload('CROSS_PROJECT_CONTEXT_VIOLATION', str(exc)),
    )


@app.exception_handler(ProposalLifecycleError)
async def proposal_lifecycle_exception_handler(request: Request, exc: ProposalLifecycleError) -> JSONResponse:
    return JSONResponse(
        status_code=400,
        content=build_error_payload('PROPOSAL_LIFECYCLE_ERROR', str(exc)),
    )


@app.exception_handler(GenerationSchemaValidationError)
async def generation_schema_validation_exception_handler(request: Request, exc: GenerationSchemaValidationError) -> JSONResponse:
    return JSONResponse(
        status_code=422,
        content=build_error_payload('GENERATION_SCHEMA_VALIDATION_ERROR', str(exc)),
    )


@app.exception_handler(LLMError)
async def llm_error_exception_handler(request: Request, exc: LLMError) -> JSONResponse:
    """Return a safe, normalised error for any LLM provider failure."""
    from app.schemas.llm import LLMErrorCode

    status_map = {
        LLMErrorCode.INVALID_CREDENTIALS: 401,
        LLMErrorCode.UNSUPPORTED_PROVIDER: 400,
        LLMErrorCode.UNSUPPORTED_MODEL: 400,
        LLMErrorCode.INVALID_REQUEST: 400,
        LLMErrorCode.UNSUPPORTED_PARAMETER: 400,
        LLMErrorCode.RATE_LIMIT_EXCEEDED: 429,
        LLMErrorCode.QUOTA_EXHAUSTED: 429,
        LLMErrorCode.REQUEST_TIMEOUT: 504,
        LLMErrorCode.NETWORK_ERROR: 502,
        LLMErrorCode.PROVIDER_OUTAGE: 503,
        LLMErrorCode.INVALID_RESPONSE: 502,
        LLMErrorCode.UNSUPPORTED_CAPABILITY: 400,
        LLMErrorCode.PROVIDER_NOT_CONFIGURED: 400,
        LLMErrorCode.INTERNAL_ERROR: 500,
    }
    http_status = status_map.get(exc.code, 500)
    return JSONResponse(
        status_code=http_status,
        content=build_error_payload(exc.code.value, str(exc)),
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    details: list[dict[str, str]] = []
    for error in exc.errors():
        location = ' -> '.join(str(item) for item in error.get('loc', []))
        details.append({
            'field': location,
            'message': error.get('msg', 'Invalid request.'),
        })
    return JSONResponse(
        status_code=422,
        content=build_error_payload('VALIDATION_ERROR', 'Request validation failed.', details),
    )


@app.middleware('http')
async def error_middleware(request: Request, call_next):
    try:
        return await call_next(request)
    except Exception:
        return JSONResponse(
            status_code=500,
            content=build_error_payload('INTERNAL_SERVER_ERROR', 'An unexpected server error occurred.'),
        )


@app.on_event('startup')
def startup_event() -> None:
    init_db()


@app.get('/')
def read_root() -> dict[str, str]:
    return {'message': 'CodePilot backend is running'}


@app.get(f"{settings.api_prefix}/health", response_model=HealthResponse)
def get_health() -> HealthResponse:
    return HealthResponse(status='ok', service=settings.service_name)


@app.get(f"{settings.api_prefix}/health/dependencies", response_model=DependencyHealthResponse)
def get_dependency_status() -> DependencyHealthResponse:
    return get_dependency_health()
