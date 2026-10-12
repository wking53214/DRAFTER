"""Seated in Warden's loop, the Drafter closes a finding and then runs dry."""

from pathlib import Path

from warden.authorization import grant
from warden.tagteam import TagTeam

from drafter import Drafter
from support import full_gate_kwargs, init_repo, many_tests


def test_the_loop_converges_on_a_fixed_readme(tmp_path: Path):
    (tmp_path / "pkg").mkdir()
    (tmp_path / "pkg" / "__init__.py").write_text("V = 1\n", encoding="utf-8")
    (tmp_path / "tests").mkdir()
    (tmp_path / "tests" / "test_a.py").write_text(many_tests(79), encoding="utf-8")
    (tmp_path / "README.md").write_text("# T\n\nThe suite is healthy: 16 tests passed.\n", encoding="utf-8")
    init_repo(tmp_path)
    auth = grant("william", "transform", str(tmp_path.resolve()), "documentation", "test")
    # Real Ghost scans the folder, so the Judge gets Ghost's baseline report it needs.
    result = TagTeam(drafter=Drafter(), **full_gate_kwargs()).run(tmp_path, authorization=auth)
    assert result.converged and result.decision == "ACCEPT", result.notes
    assert [c.outcome for c in result.cycles] == ["APPLIED", "NOTHING_TO_PROPOSE"]
    assert "at least 79" in (tmp_path / "README.md").read_text(encoding="utf-8")
