"""CRUD operations for todos."""

from __future__ import annotations

import json
import sqlite3
from datetime import date

from assistant.models.todo import Todo, Priority, Status


def add_todo(conn: sqlite3.Connection, todo: Todo) -> Todo:
    cur = conn.execute(
        "INSERT INTO todos (title, description, priority, status, due_date, tags_json) VALUES (?, ?, ?, ?, ?, ?)",
        (todo.title, todo.description, todo.priority.value, todo.status.value,
         str(todo.due_date) if todo.due_date else None, json.dumps(todo.tags)),
    )
    conn.commit()
    todo.id = cur.lastrowid
    return todo


def get_todo(conn: sqlite3.Connection, todo_id: int) -> Todo | None:
    row = conn.execute("SELECT * FROM todos WHERE id = ?", (todo_id,)).fetchone()
    return Todo.from_row(row) if row else None


def list_todos(
    conn: sqlite3.Connection,
    status: Status | None = None,
    priority: Priority | None = None,
    include_done: bool = False,
) -> list[Todo]:
    query = "SELECT * FROM todos WHERE 1=1"
    params = []
    if status:
        query += " AND status = ?"
        params.append(status.value)
    elif not include_done:
        query += " AND status != 'done'"
    if priority:
        query += " AND priority = ?"
        params.append(priority.value)
    query += " ORDER BY CASE priority WHEN 'urgent' THEN 0 WHEN 'high' THEN 1 WHEN 'medium' THEN 2 WHEN 'low' THEN 3 END, due_date IS NULL, due_date, created_at"
    rows = conn.execute(query, params).fetchall()
    return [Todo.from_row(r) for r in rows]


def update_todo(conn: sqlite3.Connection, todo: Todo) -> None:
    conn.execute(
        """UPDATE todos SET title=?, description=?, priority=?, status=?, due_date=?, tags_json=?, completed_at=?
           WHERE id=?""",
        (todo.title, todo.description, todo.priority.value, todo.status.value,
         str(todo.due_date) if todo.due_date else None, json.dumps(todo.tags),
         todo.completed_at, todo.id),
    )
    conn.commit()


def complete_todo(conn: sqlite3.Connection, todo_id: int) -> Todo | None:
    todo = get_todo(conn, todo_id)
    if not todo:
        return None
    todo.status = Status.DONE
    from datetime import datetime
    todo.completed_at = datetime.now().isoformat()
    update_todo(conn, todo)
    return todo


def delete_todo(conn: sqlite3.Connection, todo_id: int) -> bool:
    cur = conn.execute("DELETE FROM todos WHERE id = ?", (todo_id,))
    conn.commit()
    return cur.rowcount > 0


def get_overdue(conn: sqlite3.Connection) -> list[Todo]:
    today = date.today().isoformat()
    rows = conn.execute(
        "SELECT * FROM todos WHERE due_date < ? AND status != 'done' ORDER BY due_date",
        (today,),
    ).fetchall()
    return [Todo.from_row(r) for r in rows]


def get_due_soon(conn: sqlite3.Connection, days: int = 3) -> list[Todo]:
    from datetime import timedelta
    today = date.today()
    soon = (today + timedelta(days=days)).isoformat()
    rows = conn.execute(
        "SELECT * FROM todos WHERE due_date <= ? AND due_date >= ? AND status != 'done' ORDER BY due_date",
        (soon, today.isoformat()),
    ).fetchall()
    return [Todo.from_row(r) for r in rows]
