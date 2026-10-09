"""The dead_code fixer proposes exact removals from Ghost's facts; Warden gates them."""

from pathlib import Path

import pytest

import warden.tagteam as tagteam
from warden.authorization import grant
from warden.models import defects_from_ghost
from warden.tagteam import TagTeam

from drafter import Drafter

SOURCE = "def keep():\n    return 1\n\n\ndef unused():\n    return 2\n"


def _finding(file="pkg/mod.py", name="unused", kind="function", start=5, end=6, hook="no"):
    return {"id": "ghost-dead1", "severity": "minor", "status": "confirmed", "summary": "unused",
            "detector": "dead_code",
            "attributes": {"name": name, "kind": kind, "line_start": str(start),
                           "line_end": str(end), "framework_hook": hook},
            "evidence": {"file": file, "line_start": start, "line_end": end}}


def _repo(root: Path, source: str = SOURCE, test: str = "from pkg.mod import keep\n\ndef test_k():\n    assert keep() == 1\n"):
    (root / "pkg").mkdir()
    (root / "pkg" / "__init__.py").write_text("", encoding="utf-8")
    (root / "pkg" / "mod.py").write_text(source, encoding="utf-8")
    (root / "tests").mkdir()
    (root / "tests" / "test_k.py").write_text(test, encoding="utf-8")
    (root / "pyproject.toml").write_text('[project]\nname = "d"\nversion = "0.0.1"\n', encoding="utf-8")


def _propose(root: Path, **kw):
    return Drafter().propose(root, defects_from_ghost([_finding(**kw)]), "base")


def test_it_proposes_taking_out_exactly_the_flagged_lines(tmp_path):
    _repo(tmp_path)
    proposal = _propose(tmp_path)
    (edit,) = proposal.edits
    assert edit.kind == "replace" and edit.old == "def unused():\n    return 2\n" and edit.new == ""
    assert proposal.transformation_scope == "code"


def test_a_framework_hook_is_never_proposed(tmp_path):
    _repo(tmp_path)
    assert _propose(tmp_path, hook="yes") is None


@pytest.mark.parametrize("change", [
    {"name": "other"}, {"kind": "class"}, {"start": 4, "end": 6}, {"end": 99}, {"file": "../x.py"},
    {"file": "pkg/missing.py"},
])
def test_it_refuses_when_the_facts_do_not_match_the_file(tmp_path, change):
    _repo(tmp_path)
    assert _propose(tmp_path, **change) is None


def test_it_refuses_when_the_same_block_appears_twice(tmp_path):
    _repo(tmp_path, "def unused():\n    return 2\n\n\ndef unused():\n    return 2\n")
    assert _propose(tmp_path, start=1, end=2) is None


@pytest.fixture
def ghost(monkeypatch):
    def scan(target, **kw):
        text = (Path(target) / "pkg" / "mod.py").read_text(encoding="utf-8")
        return () if "WARDEN COMMENTED OUT" in text else (_finding(),)

    monkeypatch.setattr(tagteam, "ghost_scan", scan)
    monkeypatch.setattr(TagTeam, "_calibrate", lambda self, python, notes: True)


def _run(root: Path):
    auth = grant("william", "transform", str(root.resolve()), "code", "test")
    return TagTeam(drafter=Drafter(), ghost_tools_root=Path(".")).run(
        root, findings=[_finding()], authorization=auth)


def test_in_the_loop_unused_code_is_commented_out_with_a_timestamp(tmp_path, ghost):
    _repo(tmp_path)
    result = _run(tmp_path)
    text = (tmp_path / "pkg" / "mod.py").read_text(encoding="utf-8")
    assert result.decision == "ACCEPT"
    assert "# WARDEN COMMENTED OUT 20" in text and "# def unused():" in text
    assert "def keep():\n    return 1" in text and "\ndef unused" not in text


def test_in_the_loop_code_the_suite_runs_by_name_is_left_alone(tmp_path, ghost):
    """Nothing imports it and Ghost says it is unused, but the suite reaches it by string."""
    _repo(tmp_path, test=(
        "import importlib\n\ndef test_dynamic():\n"
        "    mod = importlib.import_module('pkg.mod')\n"
        "    assert getattr(mod, 'un' + 'used')() == 2\n"))
    result = _run(tmp_path)
    assert result.decision == "REJECT"
    assert (tmp_path / "pkg" / "mod.py").read_text(encoding="utf-8") == SOURCE
    assert any("keep test FAILED" in n for n in result.notes)
