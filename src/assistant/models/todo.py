"""Domain model for todos."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import date, datetime
from enum import Enum


class Priority(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"


class Status(Enum):
    TODO = "todo"
    IN_PROGRESS = "in_progress"
    DONE = "done"


@dataclass
class Todo:
    title: str
    description: str = ""
    priority: Priority = Priority.MEDIUM
    status: Status = Status.TODO
    due_date: date | None = None
    tags: list[str] = field(default_factory=list)
    id: int | None = None
    created_at: datetime | None = None
    completed_at: datetime | None = None

    @classmethod
    def from_row(cls, row) -> Todo:
        tags = json.loads(row["tags_json"]) if row["tags_json"] else []
        due = date.fromisoformat(row["due_date"]) if row["due_date"] else None
        return cls(
            id=row["id"],
            title=row["title"],
            description=row["description"] or "",
            priority=Priority(row["priority"]),
            status=Status(row["status"]),
            due_date=due,
            tags=tags,
            created_at=row["created_at"],
            completed_at=row["completed_at"],
        )

    @property
    def is_overdue(self) -> bool:
        return (
            self.due_date is not None
            and self.due_date < date.today()
            and self.status != Status.DONE
        )
