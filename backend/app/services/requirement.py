from __future__ import annotations

from collections.abc import Sequence
from typing import TYPE_CHECKING

from app.models.requirement import Requirement
from app.repositories.project import ProjectRepository
from app.repositories.requirement import RequirementRepository
from app.schemas.requirement import RequirementCreate, RequirementUpdate
from app.services.project import ProjectNotFoundError

if TYPE_CHECKING:
    from app.models.task import Task
    from app.repositories.task import TaskRepository



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


class CrossProjectAssociationError(Exception):
    def __init__(self, requirement_id: str, requirement_project_id: str, task_id: str, task_project_id: str):
        super().__init__(
            f'Cannot associate requirement {requirement_id} (project {requirement_project_id}) '
            f'with task {task_id} (project {task_project_id}). Both entities must belong to the same project.'
        )
        self.requirement_id = requirement_id
        self.requirement_project_id = requirement_project_id
        self.task_id = task_id
        self.task_project_id = task_project_id


class RequirementTaskAlreadyLinkedError(Exception):
    def __init__(self, requirement_id: str, task_id: str):
        super().__init__(f'Requirement {requirement_id} and task {task_id} are already linked.')
        self.requirement_id = requirement_id
        self.task_id = task_id


class RequirementTaskNotLinkedError(Exception):
    def __init__(self, requirement_id: str, task_id: str):
        super().__init__(f'Requirement {requirement_id} and task {task_id} are not linked.')
        self.requirement_id = requirement_id
        self.task_id = task_id


class RequirementService:
    def __init__(
        self,
        repository: RequirementRepository,
        project_repository: ProjectRepository,
        task_repository: TaskRepository | None = None,
    ):
        self.repository = repository
        self.project_repository = project_repository
        self.task_repository = task_repository

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

    def list_tasks_for_requirement(self, project_id: str, requirement_id: str) -> Sequence[Task]:
        requirement = self._require_requirement_for_project(project_id, requirement_id)
        return self.repository.get_associated_tasks(requirement)

    def link_task(self, project_id: str, requirement_id: str, task_id: str) -> Task:
        from app.services.task import TaskNotFoundError

        requirement = self._require_requirement_for_project(project_id, requirement_id)

        if self.task_repository is None:
            raise ValueError('TaskRepository is required for task association operations.')

        task = self.task_repository.get_by_id(task_id)
        if task is None:
            raise TaskNotFoundError(task_id)

        if task.project_id != requirement.project_id:
            raise CrossProjectAssociationError(requirement.id, requirement.project_id, task.id, task.project_id)

        if self.repository.is_task_linked(requirement, task):
            raise RequirementTaskAlreadyLinkedError(requirement.id, task.id)

        self.repository.link_task(requirement, task)
        return task

    def unlink_task(self, project_id: str, requirement_id: str, task_id: str) -> bool:
        from app.services.task import TaskNotFoundError

        requirement = self._require_requirement_for_project(project_id, requirement_id)

        if self.task_repository is None:
            raise ValueError('TaskRepository is required for task association operations.')

        task = self.task_repository.get_by_id(task_id)
        if task is None:
            raise TaskNotFoundError(task_id)

        if task.project_id != requirement.project_id:
            raise CrossProjectAssociationError(requirement.id, requirement.project_id, task.id, task.project_id)

        if not self.repository.is_task_linked(requirement, task):
            raise RequirementTaskNotLinkedError(requirement.id, task.id)

        return self.repository.unlink_task(requirement, task)



__all__ = [
    'CrossProjectAssociationError',
    'RequirementNotFoundError',
    'RequirementProjectMismatchError',
    'RequirementService',
    'RequirementTaskAlreadyLinkedError',
    'RequirementTaskNotLinkedError',
]
