"""Tests for family repository."""

from datetime import date

from assistant.models.family import FamilyMember, ImportantDate, Note, Relationship
from assistant.storage import family_repo


def test_add_and_list_members(db):
    member = FamilyMember(name="Test User", relationship=Relationship.SELF, birthday=date(1990, 5, 15))
    family_repo.add_member(db, member)

    members = family_repo.list_members(db)
    assert len(members) == 1
    assert members[0].name == "Test User"
    assert members[0].birthday == date(1990, 5, 15)


def test_get_member_by_name(db):
    family_repo.add_member(db, FamilyMember(name="Alice", relationship=Relationship.SPOUSE))
    found = family_repo.get_member_by_name(db, "alice")
    assert found is not None
    assert found.name == "Alice"


def test_add_note(db):
    family_repo.add_member(db, FamilyMember(name="Bob", relationship=Relationship.CHILD))
    member = family_repo.get_member_by_name(db, "Bob")

    note = Note(content="Loves dinosaurs", family_member_id=member.id, tags=["interests"])
    family_repo.add_note(db, note)

    notes = family_repo.list_notes(db, member.id)
    assert len(notes) == 1
    assert notes[0].content == "Loves dinosaurs"
    assert notes[0].tags == ["interests"]


def test_add_important_date(db):
    imp = ImportantDate(label="First day of school", date=date(2026, 9, 1), recurs_yearly=True)
    family_repo.add_date(db, imp)

    dates = family_repo.list_dates(db)
    assert len(dates) == 1
    assert dates[0].label == "First day of school"


def test_search_notes(db):
    family_repo.add_note(db, Note(content="Loves dinosaurs and trucks"))
    family_repo.add_note(db, Note(content="Favorite color is blue"))

    results = family_repo.search_notes(db, "dinosaur")
    assert len(results) == 1
    assert "dinosaur" in results[0].content
