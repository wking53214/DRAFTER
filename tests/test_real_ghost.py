"""End to end: the real Ghost scan feeds the Drafter, and the real Warden loop applies the result.

These tests exist because the first versions of the fixers were only ever fed
hand-written, target-relative paths. Real Ghost spelled the path of a root-level
file with the target's folder name in front, and nothing noticed. They skip, with
a stated reason, when `ghost_buster` is not importable.
"""

from __future__ import annotations

import pytest
from warden.models import defects_from_ghost

from drafter import Drafter
from support import ghost_root, many_tests, real_findings, run_loop

MODULE = "def used():\n    return 1\n\n\ndef orphan():\n    return 2\n"
TEST_U = "from {imp} import used\n\n\ndef test_u():\n    assert used() == 1\n"


def _dead(findings):
    return [f for f in findings if f["detector"] == "dead_code"]


def _build_code(root, where):
    root.mkdir()
    pkg = root
    for part in where:
        pkg = pkg / part
        pkg.mkdir(exist_ok=True)
        (pkg / "__init__.py").write_text("", encoding="utf-8")
    (pkg / "m.py").write_text(MODULE, encoding="utf-8")
    imp = ".".join([*where, "m"]) if where else "m"
    (root / "test_u.py").write_text(TEST_U.format(imp=imp), encoding="utf-8")


@pytest.mark.parametrize("where", [(), ("pkg",), ("a", "b", "c")], ids=["root", "nested", "three-deep"])
def test_a_real_dead_code_finding_is_proposed_and_applied_cleanly(tmp_path, where):
    ghost_root()
    root = tmp_path / "tgt"
    _build_code(root, where)
    findings = _dead(real_findings(root))
    assert [f["attributes"]["name"] for f in findings] == ["orphan"]
    drafter = Drafter()
    proposal = drafter.propose(root, defects_from_ghost(findings), "base")
    assert proposal is not None, drafter.last_skipped
    expected = "/".join([*where, "m.py"])
    assert proposal.edits[0].path == expected
    assert proposal.edits[0].old == "def orphan():\n    return 2\n"

    result, _ = run_loop(root)
    assert result.converged and result.decision.startswith("ACCEPT"), result.notes
    assert [c.outcome for c in result.cycles] == ["APPLIED", "NOTHING_TO_PROPOSE"]
    text = (root.joinpath(*where) / "m.py").read_text(encoding="utf-8")
    assert "# def orphan():" in text and "def used():\n    return 1" in text


def _readme_tree(root):
    (root / "docs").mkdir(parents=True)
    (root / "test_many.py").write_text(many_tests(), encoding="utf-8")
    (root / "README.md").write_text("# Doc\n\nThe suite is healthy: 5 tests passed.\n", encoding="utf-8")
    (root / "docs" / "README.md").write_text(
        "# Docs\n\nCoverage is 95% and the suite has 5 tests passing, 3 bugs fixed.\n", encoding="utf-8")


def test_real_readme_claims_in_the_root_and_a_subfolder_are_proposed(tmp_path):
    ghost_root()
    root = tmp_path / "tgt"
    _readme_tree(root)
    findings = [f for f in real_findings(root) if f["detector"] == "doc_test_count_drift"]
    assert sorted(f["evidence"]["file"] for f in findings) == ["README.md", "docs/README.md"]
    assert all(f["attributes"]["writable"] == "yes" for f in findings)
    defects = defects_from_ghost(findings)
    seen = {}
    for defect in defects:
        proposal = Drafter().propose(root, (defect,), "base")
        assert proposal is not None
        seen[proposal.edits[0].path] = proposal.edits[0].new
    assert ("The suite is healthy: at least 40 `test_*` functions "
            "(an earlier version of this document gave 5).") in seen["README.md"]
    assert ("Coverage is 95% and the suite has at least 40 `test_*` functions "
            "(an earlier version of this document gave 5), 3 bugs fixed.") in seen["docs/README.md"]


def test_the_real_loop_fixes_both_readmes_and_converges(tmp_path):
    ghost_root()
    root = tmp_path / "tgt"
    _readme_tree(root)
    (root / "pkg").mkdir()
    result, _ = run_loop(root, scope="documentation")
    assert result.converged and result.decision.startswith("ACCEPT"), result.notes
    assert [c.outcome for c in result.cycles] == ["APPLIED", "APPLIED", "NOTHING_TO_PROPOSE"]
    for rel in ("README.md", "docs/README.md"):
        text = (root / rel).read_text(encoding="utf-8")
        assert "at least 40 `test_*` functions" in text and "5 tests" not in text
    assert [f for f in real_findings(root) if f["detector"] == "doc_test_count_drift"] == []
