from __future__ import annotations

from collections.abc import Sequence
from typing import TYPE_CHECKING

from app.models.task import Task
from app.repositories.project import ProjectRepository
from app.repositories.task import TaskRepository
from app.schemas.task import TaskCreate, TaskUpdate
from app.services.project import ProjectNotFoundError
from app.services.requirement import (
    CrossProjectAssociationError,
    RequirementNotFoundError,
    RequirementProjectMismatchError,
    RequirementTaskAlreadyLinkedError,
    RequirementTaskNotLinkedError,
)

if TYPE_CHECKING:
    from app.models.project import Project
    from app.models.requirement import Requirement
    from app.repositories.requirement import RequirementRepository


class TaskNotFoundError(Exception):
    def __init__(self, task_id: str):
        super().__init__(f"Task with id {task_id} was not found.")
        self.task_id = task_id


class TaskProjectMismatchError(Exception):
    def __init__(self, task_id: str, project_id: str, actual_project_id: str):
        super().__init__(
            f"Task with id {task_id} does not belong to project {project_id}. "
            f"It belongs to project {actual_project_id}."
        )
        self.task_id = task_id
        self.project_id = project_id
        self.actual_project_id = actual_project_id


class TaskService:
    def __init__(
        self,
        repository: TaskRepository,
        project_repository: ProjectRepository,
        requirement_repository: RequirementRepository | None = None,
    ):
        self.repository = repository
        self.project_repository = project_repository
        self.requirement_repository = requirement_repository

    def _require_project(self, project_id: str) -> Project:
        project = self.project_repository.get_by_id(project_id)
        if project is None:
            raise ProjectNotFoundError(project_id)
        return project

    def _require_task_for_project(self, project_id: str, task_id: str) -> Task:
        self._require_project(project_id)
        task = self.repository.get_by_id(task_id)
        if task is None:
            raise TaskNotFoundError(task_id)
        if task.project_id != project_id:
            raise TaskProjectMismatchError(task_id, project_id, task.project_id)
        return task

    def create_task(self, project_id: str, task_data: TaskCreate) -> Task:
        self._require_project(project_id)

        requirements_to_link: list[Requirement] = []
        if task_data.requirement_ids:
            if self.requirement_repository is None:
                raise ValueError("RequirementRepository is required to link requirements during task creation.")
            for req_id in task_data.requirement_ids:
                req = self.requirement_repository.get_by_id(req_id)
                if req is None:
                    raise RequirementNotFoundError(req_id)
                if req.project_id != project_id:
                    raise CrossProjectAssociationError(req.id, req.project_id, "new-task", project_id)
                requirements_to_link.append(req)

        task = self.repository.create(project_id, task_data)

        for req in requirements_to_link:
            self.repository.link_requirement(task, req)

        return task

    def list_tasks(self, project_id: str) -> Sequence[Task]:
        self._require_project(project_id)
        return self.repository.list_by_project(project_id)

    def get_task(self, project_id: str, task_id: str) -> Task:
        return self._require_task_for_project(project_id, task_id)

    def update_task(self, project_id: str, task_id: str, task_data: TaskUpdate) -> Task:
        task = self._require_task_for_project(project_id, task_id)

        if task_data.requirement_ids is not None:
            if self.requirement_repository is None:
                raise ValueError("RequirementRepository is required to update requirement links.")
            target_reqs: list[Requirement] = []
            for req_id in task_data.requirement_ids:
                req = self.requirement_repository.get_by_id(req_id)
                if req is None:
                    raise RequirementNotFoundError(req_id)
                if req.project_id != task.project_id:
                    raise CrossProjectAssociationError(req.id, req.project_id, task.id, task.project_id)
                target_reqs.append(req)

            current_ids = {r.id for r in task.requirements}
            target_ids = {r.id for r in target_reqs}

            for r in list(task.requirements):
                if r.id not in target_ids:
                    self.repository.unlink_requirement(task, r)

            for req in target_reqs:
                if req.id not in current_ids:
                    self.repository.link_requirement(task, req)

        return self.repository.update(task, task_data)

    def delete_task(self, project_id: str, task_id: str) -> bool:
        task = self._require_task_for_project(project_id, task_id)
        return self.repository.delete(task)

    def list_requirements_for_task(self, project_id: str, task_id: str) -> Sequence[Requirement]:
        task = self._require_task_for_project(project_id, task_id)
        return self.repository.get_associated_requirements(task)

    def link_requirement(self, project_id: str, task_id: str, requirement_id: str) -> Requirement:
        task = self._require_task_for_project(project_id, task_id)

        if self.requirement_repository is None:
            raise ValueError("RequirementRepository is required for requirement association operations.")

        requirement = self.requirement_repository.get_by_id(requirement_id)
        if requirement is None:
            raise RequirementNotFoundError(requirement_id)

        if requirement.project_id != task.project_id:
            raise CrossProjectAssociationError(requirement.id, requirement.project_id, task.id, task.project_id)

        if self.repository.is_requirement_linked(task, requirement):
            raise RequirementTaskAlreadyLinkedError(requirement.id, task.id)

        self.repository.link_requirement(task, requirement)
        return requirement

    def unlink_requirement(self, project_id: str, task_id: str, requirement_id: str) -> bool:
        task = self._require_task_for_project(project_id, task_id)

        if self.requirement_repository is None:
            raise ValueError("RequirementRepository is required for requirement association operations.")

        requirement = self.requirement_repository.get_by_id(requirement_id)
        if requirement is None:
            raise RequirementNotFoundError(requirement_id)

        if requirement.project_id != task.project_id:
            raise CrossProjectAssociationError(requirement.id, requirement.project_id, task.id, task.project_id)

        if not self.repository.is_requirement_linked(task, requirement):
            raise RequirementTaskNotLinkedError(requirement.id, task.id)

        return self.repository.unlink_requirement(task, requirement)


__all__ = [
    "CrossProjectAssociationError",
    "RequirementNotFoundError",
    "RequirementTaskAlreadyLinkedError",
    "RequirementTaskNotLinkedError",
    "TaskNotFoundError",
    "TaskProjectMismatchError",
    "TaskService",
]

