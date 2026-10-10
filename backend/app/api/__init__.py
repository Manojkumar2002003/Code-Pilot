from app.api.architectures import router as architecture_router
from app.api.projects import router as project_router
from app.api.requirements import router as requirement_router

__all__ = ['architecture_router', 'project_router', 'requirement_router']
