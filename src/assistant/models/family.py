"""Domain models for family data."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import date, datetime
from enum import Enum


class Relationship(Enum):
    SELF = "self"
    SPOUSE = "spouse"
    CHILD = "child"
    OTHER = "other"


@dataclass
class FamilyMember:
    name: str
    relationship: Relationship
    birthday: date | None = None
    preferences: dict = field(default_factory=dict)
    id: int | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

    @classmethod
    def from_row(cls, row) -> FamilyMember:
        prefs = json.loads(row["preferences_json"]) if row["preferences_json"] else {}
        bday = date.fromisoformat(row["birthday"]) if row["birthday"] else None
        return cls(
            id=row["id"],
            name=row["name"],
            relationship=Relationship(row["relationship"]),
            birthday=bday,
            preferences=prefs,
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )


@dataclass
class ImportantDate:
    label: str
    date: date
    family_member_id: int | None = None
    recurs_yearly: bool = False
    notes: str = ""
    id: int | None = None

    @classmethod
    def from_row(cls, row) -> ImportantDate:
        return cls(
            id=row["id"],
            family_member_id=row["family_member_id"],
            date=date.fromisoformat(row["date"]),
            label=row["label"],
            recurs_yearly=bool(row["recurs_yearly"]),
            notes=row["notes"] or "",
        )


@dataclass
class Note:
    content: str
    family_member_id: int | None = None
    tags: list[str] = field(default_factory=list)
    id: int | None = None
    created_at: datetime | None = None

    @classmethod
    def from_row(cls, row) -> Note:
        tags = json.loads(row["tags_json"]) if row["tags_json"] else []
        return cls(
            id=row["id"],
            family_member_id=row["family_member_id"],
            content=row["content"],
            tags=tags,
            created_at=row["created_at"],
        )
