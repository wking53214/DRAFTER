"""Finding paths: tried as given, then without the target's own folder name; always inside the target."""

import os

import pytest

from support import dead_finding, doc_finding, propose

SRC = "def used():\n    return 1\n\n\ndef orphan():\n    return 2\n"


def _target(tmp_path, name="tgt"):
    root = tmp_path / name
    root.mkdir()
    return root


def test_a_path_with_the_target_folder_name_in_front_still_finds_the_root_file(tmp_path):
    root = _target(tmp_path)
    (root / "m.py").write_text(SRC, encoding="utf-8")
    proposal, _ = propose(root, dead_finding(file="tgt/m.py"))
    assert proposal.edits[0].path == "m.py" and proposal.edits[0].old == "def orphan():\n    return 2\n"


def test_the_path_as_given_wins_over_the_stripped_path(tmp_path):
    root = _target(tmp_path)
    (root / "tgt").mkdir()
    (root / "tgt" / "m.py").write_text(SRC, encoding="utf-8")
    (root / "m.py").write_text("def other():\n    return 0\n\n\ndef orphan():\n    return 3\n", encoding="utf-8")
    proposal, _ = propose(root, dead_finding(file="tgt/m.py"))
    assert proposal.edits[0].path == "tgt/m.py" and "return 2" in proposal.edits[0].old


def test_a_markdown_path_with_the_target_folder_name_in_front_is_found(tmp_path):
    root = _target(tmp_path)
    (root / "README.md").write_text("# T\n\nThe suite: 16 tests passed.\n", encoding="utf-8")
    proposal, _ = propose(root, doc_finding(file="tgt/README.md"))
    assert proposal.edits[0].path == "README.md"


def test_a_missing_file_is_a_recorded_reason_not_a_silent_nothing(tmp_path):
    root = _target(tmp_path)
    proposal, drafter = propose(root, dead_finding(file="tgt/gone.py"))
    assert proposal is None
    ((fid, reason),) = drafter.last_skipped
    assert fid == "ghost-dead1" and "no file" in reason and "gone.py" in reason


@pytest.mark.parametrize("file", ["../m.py", "pkg/../../m.py", "tgt/../m.py"])
def test_dot_dot_is_refused(tmp_path, file):
    root = _target(tmp_path)
    (root / "m.py").write_text(SRC, encoding="utf-8")
    (tmp_path / "m.py").write_text(SRC, encoding="utf-8")
    proposal, drafter = propose(root, dead_finding(file=file))
    assert proposal is None and "'..'" in drafter.last_skipped[0][1]


def test_an_absolute_path_inside_the_target_is_fine_and_outside_is_not(tmp_path):
    root = _target(tmp_path)
    (root / "m.py").write_text(SRC, encoding="utf-8")
    other = tmp_path / "o.py"
    other.write_text(SRC, encoding="utf-8")
    assert propose(root, dead_finding(file=str(root / "m.py")))[0] is not None
    assert propose(root, dead_finding(file=str(other)))[0] is None


def test_a_symlinked_file_is_refused(tmp_path):
    root = _target(tmp_path)
    outside = tmp_path / "secret.py"
    outside.write_text(SRC, encoding="utf-8")
    os.symlink(outside, root / "m.py")
    proposal, drafter = propose(root, dead_finding(file="m.py"))
    assert proposal is None and "symlink" in drafter.last_skipped[0][1]


def test_a_symlinked_folder_is_refused(tmp_path):
    root = _target(tmp_path)
    away = tmp_path / "away"
    away.mkdir()
    (away / "m.py").write_text(SRC, encoding="utf-8")
    os.symlink(away, root / "pkg")
    proposal, drafter = propose(root, dead_finding(file="pkg/m.py"))
    assert proposal is None and "symlink" in drafter.last_skipped[0][1]


@pytest.mark.parametrize("file", ["tests/m.py", "pkg/test_m.py", "m_test.py", "conftest.py",
                                  ".github/m.py", ".venv/m.py", ".git/m.py", "Tests/m.py"])
def test_test_and_config_paths_are_never_edited(tmp_path, file):
    root = _target(tmp_path)
    path = root / file
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(SRC, encoding="utf-8")
    proposal, drafter = propose(root, dead_finding(file=file))
    assert proposal is None and "never edits" in drafter.last_skipped[0][1]


@pytest.mark.parametrize("file", ["pyproject.toml", "pytest.ini", "tox.ini", "setup.cfg", "noxfile.py",
                                  ".coveragerc", "Makefile", "tests/README.md", ".github/README.md"])
def test_config_and_test_folder_documents_are_never_edited(tmp_path, file):
    root = _target(tmp_path)
    path = root / file
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("The suite: 16 tests passed.\n", encoding="utf-8")
    kind = doc_finding if file.endswith(".md") else dead_finding
    proposal, drafter = propose(root, kind(file=file, **({"line": 1} if file.endswith(".md") else {})))
    assert proposal is None and drafter.last_skipped
