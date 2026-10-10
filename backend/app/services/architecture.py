from __future__ import annotations

from app.models.architecture import Architecture
from app.models.project import Project
from app.repositories.architecture import ArchitectureRepository
from app.repositories.project import ProjectRepository
from app.schemas.architecture import ArchitectureCreate, ArchitectureUpdate
from app.services.project import ProjectNotFoundError


class ArchitectureNotFoundError(Exception):
    def __init__(self, architecture_id: str | None = None, project_id: str | None = None):
        if project_id and not architecture_id:
            super().__init__(f"Architecture for project {project_id} was not found.")
        else:
            super().__init__(f"Architecture with id {architecture_id} was not found.")
        self.architecture_id = architecture_id
        self.project_id = project_id


class ArchitectureProjectMismatchError(Exception):
    def __init__(self, architecture_id: str, project_id: str, actual_project_id: str):
        super().__init__(
            f"Architecture with id {architecture_id} does not belong to project {project_id}. "
            f"It belongs to project {actual_project_id}."
        )
        self.architecture_id = architecture_id
        self.project_id = project_id
        self.actual_project_id = actual_project_id


class ArchitectureAlreadyExistsError(Exception):
    def __init__(self, project_id: str):
        super().__init__(f"Project {project_id} already has an architecture definition.")
        self.project_id = project_id


class ArchitectureService:
    def __init__(self, repository: ArchitectureRepository, project_repository: ProjectRepository):
        self.repository = repository
        self.project_repository = project_repository

    def _require_project(self, project_id: str) -> Project:
        project = self.project_repository.get_by_id(project_id)
        if project is None:
            raise ProjectNotFoundError(project_id)
        return project

    def _require_architecture_for_project(self, project_id: str, architecture_id: str) -> Architecture:
        self._require_project(project_id)
        architecture = self.repository.get_by_id(architecture_id)
        if architecture is None:
            raise ArchitectureNotFoundError(architecture_id=architecture_id)
        if architecture.project_id != project_id:
            raise ArchitectureProjectMismatchError(architecture_id, project_id, architecture.project_id)
        return architecture

    def create_architecture(self, project_id: str, architecture_data: ArchitectureCreate) -> Architecture:
        self._require_project(project_id)
        existing = self.repository.get_by_project_id(project_id)
        if existing is not None:
            raise ArchitectureAlreadyExistsError(project_id)
        return self.repository.create(project_id, architecture_data)

    def get_architecture_by_project(self, project_id: str) -> Architecture:
        self._require_project(project_id)
        architecture = self.repository.get_by_project_id(project_id)
        if architecture is None:
            raise ArchitectureNotFoundError(project_id=project_id)
        return architecture

    def get_architecture(self, project_id: str, architecture_id: str) -> Architecture:
        return self._require_architecture_for_project(project_id, architecture_id)

    def update_architecture(
        self,
        project_id: str,
        architecture_id: str,
        architecture_data: ArchitectureUpdate,
    ) -> Architecture:
        architecture = self._require_architecture_for_project(project_id, architecture_id)
        return self.repository.update(architecture, architecture_data)

    def delete_architecture(self, project_id: str, architecture_id: str) -> bool:
        architecture = self._require_architecture_for_project(project_id, architecture_id)
        return self.repository.delete(architecture)

    def update_architecture_by_project(
        self,
        project_id: str,
        architecture_data: ArchitectureUpdate,
    ) -> Architecture:
        architecture = self.get_architecture_by_project(project_id)
        return self.repository.update(architecture, architecture_data)

    def delete_architecture_by_project(self, project_id: str) -> bool:
        architecture = self.get_architecture_by_project(project_id)
        return self.repository.delete(architecture)


__all__ = [
    "ArchitectureAlreadyExistsError",
    "ArchitectureNotFoundError",
    "ArchitectureProjectMismatchError",
    "ArchitectureService",
]
