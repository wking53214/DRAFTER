"""A public name is not proposed for removal unless the caller opts in (item 15)."""

import pytest

from warden.models import defects_from_ghost

from drafter import Drafter

pytestmark = pytest.mark.keeps_default

SOURCE = "def keep():\n    return 1\n\n\ndef unused():\n    return 2\n\n\ndef _private_unused():\n    return 3\n"


def _finding(name, start, end):
    return {"id": "ghost-d", "severity": "minor", "status": "confirmed", "summary": "unused",
            "detector": "dead_code",
            "attributes": {"name": name, "kind": "function", "line_start": str(start), "line_end": str(end),
                           "framework_hook": "no", "dynamic_lookup_possible": "no"},
            "evidence": {"file": "pkg/mod.py", "line_start": start, "line_end": end}}


def _repo(root):
    (root / "pkg").mkdir()
    (root / "pkg" / "__init__.py").write_text("", encoding="utf-8")
    (root / "pkg" / "mod.py").write_text(SOURCE, encoding="utf-8")


def _propose(root, name, start, end):
    d = Drafter()
    return d, d.propose(root, defects_from_ghost([_finding(name, start, end)]), "base")


def test_a_public_name_is_refused_by_default(tmp_path, monkeypatch):
    monkeypatch.delenv("DRAFTER_ALLOW_PUBLIC_REMOVAL", raising=False)
    _repo(tmp_path)
    d, proposal = _propose(tmp_path, "unused", 5, 6)
    assert proposal is None
    assert any("public name" in reason for _, reason in d.last_skipped)


def test_a_private_name_is_still_proposed(tmp_path, monkeypatch):
    monkeypatch.delenv("DRAFTER_ALLOW_PUBLIC_REMOVAL", raising=False)
    _repo(tmp_path)
    _, proposal = _propose(tmp_path, "_private_unused", 9, 10)
    assert proposal is not None


def test_opting_in_allows_a_public_name(tmp_path, monkeypatch):
    monkeypatch.setenv("DRAFTER_ALLOW_PUBLIC_REMOVAL", "1")
    _repo(tmp_path)
    _, proposal = _propose(tmp_path, "unused", 5, 6)
    assert proposal is not None


def test_a_removal_report_names_the_folders_the_search_skipped(tmp_path, monkeypatch):
    monkeypatch.delenv("DRAFTER_ALLOW_PUBLIC_REMOVAL", raising=False)
    _repo(tmp_path)
    d, proposal = _propose(tmp_path, "_private_unused", 9, 10)
    assert proposal is not None
    note = d.describe_skipped()[-1]
    assert note.startswith("note: the search for other uses") and "node_modules" in note and ".venv" in note


def test_no_folder_note_when_nothing_was_removed(tmp_path, monkeypatch):
    monkeypatch.delenv("DRAFTER_ALLOW_PUBLIC_REMOVAL", raising=False)
    _repo(tmp_path)
    d, proposal = _propose(tmp_path, "unused", 5, 6)
    assert proposal is None
    assert not any(line.startswith("note:") for line in d.describe_skipped())
