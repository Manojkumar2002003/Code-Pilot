from __future__ import annotations

from typing import Sequence

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.task import Task
from app.schemas.task import TaskCreate, TaskUpdate


class TaskRepository:
    def __init__(self, session: Session):
        self.session = session

    def create(self, project_id: str, task_data: TaskCreate) -> Task:
        priority_value = task_data.priority.value if hasattr(task_data.priority, "value") else task_data.priority
        status_value = task_data.status.value if hasattr(task_data.status, "value") else task_data.status
        task = Task(
            project_id=project_id,
            title=task_data.title,
            description=task_data.description,
            priority=priority_value,
            status=status_value,
        )
        self.session.add(task)
        self.session.commit()
        self.session.refresh(task)
        return task

    def get_by_id(self, task_id: str) -> Task | None:
        return self.session.get(Task, task_id)

    def list_by_project(self, project_id: str) -> Sequence[Task]:
        return self.session.execute(
            select(Task)
            .where(Task.project_id == project_id)
            .order_by(Task.created_at.desc(), Task.id.desc())
        ).scalars().all()

    def update(self, task: Task, update_data: TaskUpdate) -> Task:
        if update_data.title is not None:
            task.title = update_data.title
        if update_data.description is not None:
            task.description = update_data.description
        if update_data.status is not None:
            task.status = update_data.status.value if hasattr(update_data.status, "value") else update_data.status
        if update_data.priority is not None:
            task.priority = update_data.priority.value if hasattr(update_data.priority, "value") else update_data.priority

        self.session.add(task)
        self.session.commit()
        self.session.refresh(task)
        return task

    def delete(self, task: Task) -> bool:
        if task is None:
            raise ValueError("Task cannot be None.")

        existing = self.session.get(Task, task.id)
        if existing is None:
            raise ValueError(f"Task with id {task.id} was not found.")

        self.session.delete(existing)
        self.session.commit()
        return True


__all__ = ["TaskRepository"]
