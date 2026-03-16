"""Todoist service — read tasks via REST API for briefing integration."""

from __future__ import annotations

import json
import urllib.request
from datetime import date

from assistant import config

_BASE = "https://api.todoist.com/api/v1"


def _get(path: str, params: dict | None = None) -> list | dict:
    """Make an authenticated GET request to the Todoist API."""
    url = f"{_BASE}{path}"
    if params:
        qs = "&".join(f"{k}={v}" for k, v in params.items() if v is not None)
        url = f"{url}?{qs}"
    req = urllib.request.Request(url, headers={
        "Authorization": f"Bearer {config.TODOIST_API_TOKEN}",
    })
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read())


def get_active_tasks() -> list[dict]:
    """Get all active (non-completed) tasks."""
    data = _get("/tasks")
    return data.get("results", data) if isinstance(data, dict) else data


def get_this_week() -> list[dict]:
    """Get tasks tagged with This_Week label."""
    tasks = get_active_tasks()
    return [t for t in tasks if "This_Week" in t.get("labels", [])]


def get_overdue() -> list[dict]:
    """Get tasks with due dates in the past."""
    today = date.today().isoformat()
    tasks = get_active_tasks()
    return [
        t for t in tasks
        if t.get("due") and t["due"].get("date") and t["due"]["date"] < today
    ]


def get_due_soon(days: int = 3) -> list[dict]:
    """Get tasks due within the next N days (not overdue)."""
    today = date.today()
    tasks = get_active_tasks()
    result = []
    for t in tasks:
        due = t.get("due")
        if not due or not due.get("date"):
            continue
        try:
            due_date = date.fromisoformat(due["date"][:10])
        except ValueError:
            continue
        delta = (due_date - today).days
        if 0 <= delta <= days:
            result.append(t)
    return result


def get_waiting() -> list[dict]:
    """Get tasks tagged with Waiting label."""
    tasks = get_active_tasks()
    return [t for t in tasks if "Waiting" in t.get("labels", [])]


# --- Helpers for briefing rendering ---

PRIORITY_MAP = {1: "urgent", 2: "high", 3: "medium", 4: "normal"}


def task_priority_label(task: dict) -> str:
    """Convert Todoist priority (1=urgent, 4=normal) to human label."""
    return PRIORITY_MAP.get(task.get("priority", 4), "normal")


def task_due_date(task: dict) -> date | None:
    """Extract due date from a task, or None."""
    due = task.get("due")
    if not due or not due.get("date"):
        return None
    try:
        return date.fromisoformat(due["date"][:10])
    except ValueError:
        return None
