"""The doc-count fixer acts on Ghost's facts, and only where it is safe."""

from pathlib import Path

from elegant.models import defects_from_ghost

from proposer import Proposer


def _finding(file="README.md", line=3, documented=16, lower=79, writable="yes", detector="doc_test_count_drift"):
    return {"id": "ghost-abc", "severity": "minor", "status": "confirmed", "summary": "stale count",
            "detector": detector,
            "attributes": {"documented_count": str(documented), "static_lower_bound": str(lower),
                           "writable": writable},
            "evidence": {"file": file, "line_start": line}}


def _readme(root: Path, body: str) -> None:
    (root / "README.md").write_text(body, encoding="utf-8")


def _propose(root: Path, **kw):
    return Proposer().propose(root, defects_from_ghost([_finding(**kw)]), "base")


def test_a_stale_claim_becomes_a_truthful_sentence(tmp_path: Path):
    _readme(tmp_path, "# T\n\nAll 16 tests passed on CI.\n\nOther text.\n")
    proposal = _propose(tmp_path, line=3)
    (edit,) = proposal.edits
    assert "The suite holds at least 79 `test_*` functions" in edit.new
    assert "an earlier version of this document gave 16" in edit.new
    assert edit.new.endswith("\n\nOther text.\n") and edit.old.startswith("# T")


def test_list_markers_survive(tmp_path: Path):
    _readme(tmp_path, "# T\n\n- 16 tests passed.\n")
    (edit,) = _propose(tmp_path, line=3).edits
    assert "\n- The suite holds at least 79" in edit.new


def test_ghost_saying_not_writable_means_no_proposal(tmp_path: Path):
    _readme(tmp_path, "# T\n\nAll 16 tests passed.\n")
    assert _propose(tmp_path, line=3, writable="no") is None


def test_tables_and_headings_are_left_alone(tmp_path: Path):
    _readme(tmp_path, "| suite | 16 tests passed |\n")
    assert _propose(tmp_path, line=1) is None


def test_a_file_outside_the_target_is_never_touched(tmp_path: Path):
    outside = tmp_path / "outside.md"
    outside.write_text("16 tests passed.\n", encoding="utf-8")
    inner = tmp_path / "repo"
    inner.mkdir()
    assert _propose(inner, file=str(outside), line=1) is None
    assert _propose(inner, file="../outside.md", line=1) is None


def test_a_claim_already_fixed_means_nothing_left(tmp_path: Path):
    _readme(tmp_path, "# T\n\nThe suite is covered.\n")
    assert _propose(tmp_path, line=3) is None


def test_unknown_detectors_are_not_this_proposers_business(tmp_path: Path):
    _readme(tmp_path, "All 16 tests passed.\n")
    assert _propose(tmp_path, line=1, detector="long_function") is None


def test_one_change_per_proposal(tmp_path: Path):
    _readme(tmp_path, "A. 16 tests passed.\n\nB. 16 tests passed.\n")
    defects = defects_from_ghost([_finding(line=1), _finding(line=3)])
    proposal = Proposer().propose(tmp_path, defects, "base")
    assert len(proposal.edits) == 1 and len(proposal.known_defects) == 1
