"""CRUD operations for family data."""

from __future__ import annotations

import json
import sqlite3
from datetime import date

from assistant.models.family import FamilyMember, ImportantDate, Note, Relationship


# --- Family Members ---

def add_member(conn: sqlite3.Connection, member: FamilyMember) -> FamilyMember:
    cur = conn.execute(
        "INSERT INTO family_members (name, relationship, birthday, preferences_json) VALUES (?, ?, ?, ?)",
        (member.name, member.relationship.value, str(member.birthday) if member.birthday else None,
         json.dumps(member.preferences)),
    )
    conn.commit()
    member.id = cur.lastrowid
    return member


def get_member(conn: sqlite3.Connection, member_id: int) -> FamilyMember | None:
    row = conn.execute("SELECT * FROM family_members WHERE id = ?", (member_id,)).fetchone()
    return FamilyMember.from_row(row) if row else None


def get_member_by_name(conn: sqlite3.Connection, name: str) -> FamilyMember | None:
    row = conn.execute(
        "SELECT * FROM family_members WHERE LOWER(name) = LOWER(?)", (name,)
    ).fetchone()
    return FamilyMember.from_row(row) if row else None


def list_members(conn: sqlite3.Connection) -> list[FamilyMember]:
    rows = conn.execute("SELECT * FROM family_members ORDER BY name").fetchall()
    return [FamilyMember.from_row(r) for r in rows]


def update_member(conn: sqlite3.Connection, member: FamilyMember) -> None:
    conn.execute(
        """UPDATE family_members
           SET name=?, relationship=?, birthday=?, preferences_json=?, updated_at=CURRENT_TIMESTAMP
           WHERE id=?""",
        (member.name, member.relationship.value,
         str(member.birthday) if member.birthday else None,
         json.dumps(member.preferences), member.id),
    )
    conn.commit()


def delete_member(conn: sqlite3.Connection, member_id: int) -> None:
    conn.execute("DELETE FROM family_members WHERE id = ?", (member_id,))
    conn.commit()


# --- Important Dates ---

def add_date(conn: sqlite3.Connection, imp_date: ImportantDate) -> ImportantDate:
    cur = conn.execute(
        "INSERT INTO important_dates (family_member_id, date, label, recurs_yearly, notes) VALUES (?, ?, ?, ?, ?)",
        (imp_date.family_member_id, str(imp_date.date), imp_date.label,
         int(imp_date.recurs_yearly), imp_date.notes),
    )
    conn.commit()
    imp_date.id = cur.lastrowid
    return imp_date


def get_upcoming_dates(conn: sqlite3.Connection, days: int = 30) -> list[ImportantDate]:
    """Get important dates coming up in the next N days, accounting for yearly recurrence."""
    all_dates = conn.execute("SELECT * FROM important_dates").fetchall()
    today = date.today()
    upcoming = []
    for row in all_dates:
        d = ImportantDate.from_row(row)
        if d.recurs_yearly:
            this_year = d.date.replace(year=today.year)
            if this_year < today:
                this_year = this_year.replace(year=today.year + 1)
            delta = (this_year - today).days
        else:
            delta = (d.date - today).days
        if 0 <= delta <= days:
            upcoming.append(d)
    return sorted(upcoming, key=lambda x: x.date)


def list_dates(conn: sqlite3.Connection, family_member_id: int | None = None) -> list[ImportantDate]:
    if family_member_id:
        rows = conn.execute(
            "SELECT * FROM important_dates WHERE family_member_id = ? ORDER BY date",
            (family_member_id,),
        ).fetchall()
    else:
        rows = conn.execute("SELECT * FROM important_dates ORDER BY date").fetchall()
    return [ImportantDate.from_row(r) for r in rows]


# --- Notes ---

def add_note(conn: sqlite3.Connection, note: Note) -> Note:
    cur = conn.execute(
        "INSERT INTO notes (family_member_id, content, tags_json) VALUES (?, ?, ?)",
        (note.family_member_id, note.content, json.dumps(note.tags)),
    )
    conn.commit()
    note.id = cur.lastrowid
    return note


def list_notes(conn: sqlite3.Connection, family_member_id: int | None = None) -> list[Note]:
    if family_member_id:
        rows = conn.execute(
            "SELECT * FROM notes WHERE family_member_id = ? ORDER BY created_at DESC",
            (family_member_id,),
        ).fetchall()
    else:
        rows = conn.execute("SELECT * FROM notes ORDER BY created_at DESC").fetchall()
    return [Note.from_row(r) for r in rows]


def search_notes(conn: sqlite3.Connection, query: str) -> list[Note]:
    rows = conn.execute(
        "SELECT * FROM notes WHERE content LIKE ? ORDER BY created_at DESC",
        (f"%{query}%",),
    ).fetchall()
    return [Note.from_row(r) for r in rows]
