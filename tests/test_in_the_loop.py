"""Seated in Elegant's loop, the Proposer closes a finding and then runs dry."""

from pathlib import Path

from elegant.authorization import grant
from elegant.tagteam import TagTeam

from proposer import Proposer
from test_fixer import _finding


def test_the_loop_converges_on_a_fixed_readme(tmp_path: Path):
    (tmp_path / "pkg").mkdir()
    (tmp_path / "pkg" / "__init__.py").write_text("V = 1\n", encoding="utf-8")
    (tmp_path / "tests").mkdir()
    (tmp_path / "tests" / "test_a.py").write_text("def test_a():\n    assert True\n", encoding="utf-8")
    (tmp_path / "README.md").write_text("# T\n\nAll 16 tests passed.\n", encoding="utf-8")
    auth = grant("william", "transform", str(tmp_path.resolve()), "documentation", "test")
    result = TagTeam(proposer=Proposer()).run(
        tmp_path, findings=[_finding(line=3)], authorization=auth)
    assert result.converged and result.decision == "ACCEPT"
    assert [c.outcome for c in result.cycles] == ["APPLIED", "NOTHING_TO_PROPOSE"]
    assert "at least 79" in (tmp_path / "README.md").read_text(encoding="utf-8")
