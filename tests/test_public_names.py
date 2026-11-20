"""A public name is not proposed for removal unless the caller opts in; the report names the folders the search skipped."""

from pathlib import Path

from warden.models import defects_from_ghost

from drafter import Drafter
from drafter._reach import SKIPPED_FOLDERS

SOURCE = "def keep():\n    return 1\n\n\ndef unused():\n    return 2\n\n\ndef _helper():\n    return 3\n"


def _finding(name, start, end):
    return {"id": f"ghost-{name}", "severity": "minor", "status": "confirmed", "summary": "unused",
            "detector": "dead_code",
            "attributes": {"name": name, "kind": "function", "line_start": str(start), "line_end": str(end),
                           "framework_hook": "no", "dynamic_lookup_possible": "no"},
            "evidence": {"file": "mod.py", "line_start": start, "line_end": end}}


def _repo(root: Path) -> Path:
    (root / "mod.py").write_text(SOURCE, encoding="utf-8")
    return root


def test_a_public_name_is_not_proposed_by_default_and_the_reason_says_why(tmp_path):
    drafter = Drafter()
    assert drafter.propose(_repo(tmp_path), defects_from_ghost([_finding("unused", 5, 6)]), "base") is None
    fid, reason = drafter.last_skipped[0]
    assert "public name" in reason and "--allow-public-removals" in reason


def test_opting_in_proposes_the_public_name(tmp_path):
    drafter = Drafter(allow_public_removals=True)
    assert drafter.propose(_repo(tmp_path), defects_from_ghost([_finding("unused", 5, 6)]), "base") is not None


def test_a_private_name_is_proposed_without_opting_in(tmp_path):
    drafter = Drafter()
    assert drafter.propose(_repo(tmp_path), defects_from_ghost([_finding("_helper", 9, 10)]), "base") is not None


def test_a_proposed_removal_reports_the_folders_the_search_skipped(tmp_path):
    drafter = Drafter(allow_public_removals=True)
    drafter.propose(_repo(tmp_path), defects_from_ghost([_finding("unused", 5, 6)]), "base")
    note = " ".join(drafter.describe_skipped())
    assert "left out these folders" in note
    assert all(folder in note for folder in ("node_modules", ".venv", "site-packages"))
    assert "node_modules" in SKIPPED_FOLDERS


def test_no_folder_note_when_nothing_was_proposed(tmp_path):
    drafter = Drafter()
    drafter.propose(_repo(tmp_path), defects_from_ghost([_finding("unused", 5, 6)]), "base")
    assert "left out these folders" not in " ".join(drafter.describe_skipped())
