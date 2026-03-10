"""Business logic for family data."""

from __future__ import annotations

from datetime import date

from assistant import config
from assistant.models.family import FamilyMember, ImportantDate, Note, Relationship
from assistant.storage import family_repo
from assistant.storage.database import get_connection, init_db


def _get_db():
    conn = get_connection(config.DB_PATH)
    init_db(conn)
    return conn


def add_family_member(
    name: str, relationship: str, birthday: date | None = None, preferences: dict | None = None
) -> FamilyMember:
    conn = _get_db()
    member = FamilyMember(
        name=name,
        relationship=Relationship(relationship),
        birthday=birthday,
        preferences=preferences or {},
    )
    return family_repo.add_member(conn, member)


def list_family() -> list[FamilyMember]:
    return family_repo.list_members(_get_db())


def find_member(name: str) -> FamilyMember | None:
    return family_repo.get_member_by_name(_get_db(), name)


def add_important_date(
    label: str, dt: date, member_name: str | None = None, recurs_yearly: bool = False, notes: str = ""
) -> ImportantDate:
    conn = _get_db()
    member_id = None
    if member_name:
        member = family_repo.get_member_by_name(conn, member_name)
        if member:
            member_id = member.id
    imp = ImportantDate(label=label, date=dt, family_member_id=member_id, recurs_yearly=recurs_yearly, notes=notes)
    return family_repo.add_date(conn, imp)


def get_upcoming(days: int = 30) -> list[ImportantDate]:
    return family_repo.get_upcoming_dates(_get_db(), days)


def add_note(content: str, member_name: str | None = None, tags: list[str] | None = None) -> Note:
    conn = _get_db()
    member_id = None
    if member_name:
        member = family_repo.get_member_by_name(conn, member_name)
        if member:
            member_id = member.id
    note = Note(content=content, family_member_id=member_id, tags=tags or [])
    return family_repo.add_note(conn, note)


def search(query: str) -> list[Note]:
    return family_repo.search_notes(_get_db(), query)


def summarize_family() -> str:
    """Build a text summary of family data for the chat system prompt."""
    conn = _get_db()
    members = family_repo.list_members(conn)
    notes = family_repo.list_notes(conn)
    upcoming = family_repo.get_upcoming_dates(conn, days=30)

    lines = ["## Family Members"]
    for m in members:
        bday = f" (birthday: {m.birthday})" if m.birthday else ""
        lines.append(f"- {m.name}: {m.relationship.value}{bday}")
        if m.preferences:
            for k, v in m.preferences.items():
                lines.append(f"  - {k}: {v}")

    if upcoming:
        lines.append("\n## Upcoming Dates (next 30 days)")
        for d in upcoming:
            lines.append(f"- {d.date}: {d.label}")

    if notes:
        lines.append("\n## Notes")
        for n in notes[:20]:
            lines.append(f"- {n.content}")

    return "\n".join(lines)
