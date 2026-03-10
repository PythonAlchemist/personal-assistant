"""Business logic for todos."""

from __future__ import annotations

from datetime import date

from assistant import config
from assistant.models.todo import Todo, Priority, Status
from assistant.storage import todo_repo
from assistant.storage.database import get_connection, init_db


def _get_db():
    conn = get_connection(config.DB_PATH)
    init_db(conn)
    return conn


def add(title: str, due: date | None = None, priority: str = "medium",
        description: str = "", tags: list[str] | None = None) -> Todo:
    todo = Todo(
        title=title,
        description=description,
        priority=Priority(priority),
        due_date=due,
        tags=tags or [],
    )
    return todo_repo.add_todo(_get_db(), todo)


def list_all(include_done: bool = False, priority: str | None = None) -> list[Todo]:
    p = Priority(priority) if priority else None
    return todo_repo.list_todos(_get_db(), priority=p, include_done=include_done)


def get(todo_id: int) -> Todo | None:
    return todo_repo.get_todo(_get_db(), todo_id)


def complete(todo_id: int) -> Todo | None:
    return todo_repo.complete_todo(_get_db(), todo_id)


def remove(todo_id: int) -> bool:
    return todo_repo.delete_todo(_get_db(), todo_id)


def start(todo_id: int) -> Todo | None:
    conn = _get_db()
    todo = todo_repo.get_todo(conn, todo_id)
    if not todo:
        return None
    todo.status = Status.IN_PROGRESS
    todo_repo.update_todo(conn, todo)
    return todo


def update(todo_id: int, title: str | None = None, due: date | None = None,
           priority: str | None = None, description: str | None = None) -> Todo | None:
    conn = _get_db()
    todo = todo_repo.get_todo(conn, todo_id)
    if not todo:
        return None
    if title is not None:
        todo.title = title
    if due is not None:
        todo.due_date = due
    if priority is not None:
        todo.priority = Priority(priority)
    if description is not None:
        todo.description = description
    todo_repo.update_todo(conn, todo)
    return todo


def overdue() -> list[Todo]:
    return todo_repo.get_overdue(_get_db())


def due_soon(days: int = 3) -> list[Todo]:
    return todo_repo.get_due_soon(_get_db(), days)
