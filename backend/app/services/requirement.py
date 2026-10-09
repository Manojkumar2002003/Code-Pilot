from __future__ import annotations

from collections.abc import Sequence

from app.models.requirement import Requirement
from app.repositories.project import ProjectRepository
from app.repositories.requirement import RequirementRepository
from app.schemas.requirement import RequirementCreate, RequirementUpdate
from app.services.project import ProjectNotFoundError


class RequirementNotFoundError(Exception):
    def __init__(self, requirement_id: str):
        super().__init__(f'Requirement with id {requirement_id} was not found.')
        self.requirement_id = requirement_id


class RequirementProjectMismatchError(Exception):
    def __init__(self, requirement_id: str, project_id: str, actual_project_id: str):
        super().__init__(
            f'Requirement with id {requirement_id} does not belong to project {project_id}. '
            f'It belongs to project {actual_project_id}.'
        )
        self.requirement_id = requirement_id
        self.project_id = project_id
        self.actual_project_id = actual_project_id


class RequirementService:
    def __init__(self, repository: RequirementRepository, project_repository: ProjectRepository):
        self.repository = repository
        self.project_repository = project_repository

    def _require_project(self, project_id: str):
        project = self.project_repository.get_by_id(project_id)
        if project is None:
            raise ProjectNotFoundError(project_id)
        return project

    def _require_requirement_for_project(self, project_id: str, requirement_id: str) -> Requirement:
        self._require_project(project_id)
        requirement = self.repository.get_by_id(requirement_id)
        if requirement is None:
            raise RequirementNotFoundError(requirement_id)
        if requirement.project_id != project_id:
            raise RequirementProjectMismatchError(requirement_id, project_id, requirement.project_id)
        return requirement

    def create_requirement(self, project_id: str, requirement_data: RequirementCreate) -> Requirement:
        self._require_project(project_id)
        return self.repository.create(project_id, requirement_data)

    def list_requirements(self, project_id: str) -> Sequence[Requirement]:
        self._require_project(project_id)
        return self.repository.list_by_project(project_id)

    def get_requirement(self, project_id: str, requirement_id: str) -> Requirement:
        return self._require_requirement_for_project(project_id, requirement_id)

    def update_requirement(self, project_id: str, requirement_id: str, requirement_data: RequirementUpdate) -> Requirement:
        requirement = self._require_requirement_for_project(project_id, requirement_id)
        return self.repository.update(requirement, requirement_data)

    def delete_requirement(self, project_id: str, requirement_id: str) -> bool:
        requirement = self._require_requirement_for_project(project_id, requirement_id)
        return self.repository.delete(requirement)


__all__ = ['RequirementNotFoundError', 'RequirementProjectMismatchError', 'RequirementService']
