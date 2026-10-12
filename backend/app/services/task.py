from __future__ import annotations

from collections.abc import Sequence
from typing import TYPE_CHECKING

from app.models.task import Task
from app.repositories.project import ProjectRepository
from app.repositories.task import TaskRepository
from app.schemas.task import TaskCreate, TaskUpdate
from app.services.project import ProjectNotFoundError

if TYPE_CHECKING:
    from app.models.project import Project


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
    def __init__(self, repository: TaskRepository, project_repository: ProjectRepository):
        self.repository = repository
        self.project_repository = project_repository

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
        return self.repository.create(project_id, task_data)

    def list_tasks(self, project_id: str) -> Sequence[Task]:
        self._require_project(project_id)
        return self.repository.list_by_project(project_id)

    def get_task(self, project_id: str, task_id: str) -> Task:
        return self._require_task_for_project(project_id, task_id)

    def update_task(self, project_id: str, task_id: str, task_data: TaskUpdate) -> Task:
        task = self._require_task_for_project(project_id, task_id)
        return self.repository.update(task, task_data)

    def delete_task(self, project_id: str, task_id: str) -> bool:
        task = self._require_task_for_project(project_id, task_id)
        return self.repository.delete(task)


__all__ = [
    "TaskNotFoundError",
    "TaskProjectMismatchError",
    "TaskService",
]
