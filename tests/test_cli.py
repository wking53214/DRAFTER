"""`drafter --version` and `drafter propose PATH`: a read-only dry run with documented exit codes."""

import json
import logging
import os
import re
import subprocess
import sys
from pathlib import Path

import pytest

import drafter
from drafter.cli import EXIT_NO_FINDINGS, EXIT_NOTHING, EXIT_PROPOSED, EXIT_USAGE, main
from support import dead_finding, doc_finding, ghost_root, many_tests

REPO = Path(drafter.__file__).resolve().parent.parent


@pytest.fixture(autouse=True)
def _restore_logging():
    root = logging.getLogger()
    handlers, level = list(root.handlers), root.level
    yield
    root.handlers[:], root.level = handlers, level


def _tree(tmp_path: Path, readme: str = "# T\n\nThe suite is healthy: 16 tests passed.\n") -> Path:
    root = tmp_path / "tgt"
    (root / "tests").mkdir(parents=True)
    (root / "tests" / "test_a.py").write_text(many_tests(79), encoding="utf-8")
    (root / "README.md").write_text(readme, encoding="utf-8")
    (root / "m.py").write_text("def used():\n    return 1\n", encoding="utf-8")
    return root


def _findings(tmp_path: Path, *findings: dict) -> Path:
    path = tmp_path / "findings.json"
    path.write_text(json.dumps(list(findings)), encoding="utf-8")
    return path


def _snapshot(root: Path) -> dict[str, bytes]:
    return {p.relative_to(root).as_posix(): p.read_bytes() for p in sorted(root.rglob("*")) if p.is_file()}


def test_exit_codes_are_the_documented_ones():
    assert (EXIT_PROPOSED, EXIT_NOTHING, EXIT_USAGE, EXIT_NO_FINDINGS) == (0, 1, 2, 3)
    doc = sys.modules["drafter.cli"].__doc__ or ""
    for code, meaning in ((0, "a proposal was made"), (1, "nothing to propose"), (2, "usage error"),
                          (3, "findings could not be obtained")):
        assert re.search(rf"^\s+{code}\s+{meaning}", doc, re.MULTILINE), (code, meaning)


def test_version_prints_the_package_version(capsys):
    with pytest.raises(SystemExit) as stop:
        main(["--version"])
    assert stop.value.code == 0
    assert capsys.readouterr().out.strip() == f"drafter {drafter.__version__}"


def test_a_proposal_is_printed_as_json_and_nothing_is_written(tmp_path, capsys):
    root = _tree(tmp_path)
    before = _snapshot(root)
    code = main(["propose", str(root), "--findings", str(_findings(tmp_path, doc_finding(line=3)))])
    report = json.loads(capsys.readouterr().out)
    assert code == EXIT_PROPOSED
    assert _snapshot(root) == before                        # read-only: not one byte changed
    assert report["drafter_version"] == drafter.__version__
    assert report["findings"] == 1 and report["skipped"] == []
    proposal = report["proposal"]
    assert proposal["scope"] == "documentation" and proposal["affected_files"] == ["README.md"]
    (edit,) = proposal["edits"]
    assert edit["path"] == "README.md" and edit["kind"] == "write"
    assert "at least 79" in edit["new"] and "16 tests passed" in edit["old"]


def test_nothing_to_propose_is_exit_1_and_says_why(tmp_path, capsys):
    root = _tree(tmp_path)
    findings = _findings(tmp_path, dead_finding(name="no_such_name", start=1, end=2))
    code = main(["propose", str(root), "--findings", str(findings)])
    report = json.loads(capsys.readouterr().out)
    assert code == EXIT_NOTHING
    assert report["proposal"] is None
    assert report["skipped"] and report["skipped"][0]["finding"] == "ghost-dead1"
    assert report["skipped"][0]["reason"]


def test_no_findings_at_all_is_exit_1(tmp_path, capsys):
    code = main(["propose", str(_tree(tmp_path)), "--findings", str(_findings(tmp_path))])
    assert code == EXIT_NOTHING and json.loads(capsys.readouterr().out)["proposal"] is None


def test_scope_documentation_skips_a_code_fix_with_a_reason(tmp_path, capsys):
    root = _tree(tmp_path)
    code = main(["propose", str(root), "--scope", "documentation",
                 "--findings", str(_findings(tmp_path, dead_finding(name="used", start=1, end=2)))])
    report = json.loads(capsys.readouterr().out)
    assert code == EXIT_NOTHING and "documentation" in report["skipped"][0]["reason"]


@pytest.mark.parametrize("argv", [[], ["propose"], ["propose", "a", "b"], ["frobnicate"], ["propose", ".", "--nope"],
                                  ["propose", ".", "--scope", "everything"]])
def test_a_usage_error_is_exit_2(argv, capsys):
    with pytest.raises(SystemExit) as stop:
        main(argv)
    assert stop.value.code == EXIT_USAGE


def test_a_path_that_is_not_a_folder_is_exit_2(tmp_path, capsys):
    assert main(["propose", str(tmp_path / "missing")]) == EXIT_USAGE
    assert "not a folder" in capsys.readouterr().err


def test_findings_that_cannot_be_read_are_exit_3_not_exit_1(tmp_path, capsys):
    root = _tree(tmp_path)
    assert main(["propose", str(root), "--findings", str(tmp_path / "missing.json")]) == EXIT_NO_FINDINGS
    junk = tmp_path / "junk.json"
    junk.write_text("not json", encoding="utf-8")
    assert main(["propose", str(root), "--findings", str(junk)]) == EXIT_NO_FINDINGS
    assert "could not obtain findings" in capsys.readouterr().err


def test_a_ghost_that_cannot_run_is_exit_3_not_exit_1(tmp_path, capsys, monkeypatch):
    def crashed(*_a, **_k):
        raise RuntimeError("Ghost crashed (exit code 3): injected")
    monkeypatch.setattr("drafter.cli.scan", crashed)
    assert main(["propose", str(_tree(tmp_path))]) == EXIT_NO_FINDINGS
    err = capsys.readouterr().err
    assert "Ghost crashed" in err and "--findings" in err


def test_verbose_shows_a_refusal_on_stderr_and_default_is_quiet(tmp_path, capsys):
    root = _tree(tmp_path)
    findings = _findings(tmp_path, dead_finding(name="no_such_name", start=1, end=2))
    main(["propose", str(root), "--findings", str(findings)])
    assert "refused" not in capsys.readouterr().err
    main(["propose", str(root), "--findings", str(findings), "-vv"])
    assert "refused" in capsys.readouterr().err


def test_an_injected_bug_is_visible_on_stderr_and_in_the_json(tmp_path, capsys, monkeypatch):
    def boom(*_a, **_k):
        raise RuntimeError("injected bug")
    monkeypatch.setattr("drafter.fixers.doc_test_count._fix", boom)
    code = main(["propose", str(_tree(tmp_path)), "--findings", str(_findings(tmp_path, doc_finding(line=3)))])
    captured = capsys.readouterr()
    assert code == EXIT_NOTHING
    assert "internal error (RuntimeError: injected bug)" in json.loads(captured.out)["skipped"][0]["reason"]
    assert "WARNING" in captured.err and "injected bug" in captured.err


def test_python_dash_m_drafter_works_as_a_process(tmp_path):
    env = {**os.environ, "PYTHONPATH": os.pathsep.join([str(REPO), os.environ.get("PYTHONPATH", "")])}
    done = subprocess.run([sys.executable, "-m", "drafter", "--version"], capture_output=True, text=True, env=env,
                          cwd=tmp_path, check=False)
    assert done.returncode == 0 and done.stdout.strip() == f"drafter {drafter.__version__}"
    root = _tree(tmp_path)
    done = subprocess.run([sys.executable, "-m", "drafter", "propose", str(root), "--findings",
                           str(_findings(tmp_path, doc_finding(line=3)))],
                          capture_output=True, text=True, env=env, cwd=tmp_path, check=False)
    assert done.returncode == EXIT_PROPOSED and json.loads(done.stdout)["proposal"]["edits"]


def test_the_real_ghost_scan_feeds_the_dry_run(tmp_path, capsys):
    """Integration: no --findings file, Warden's own read-only Ghost scan finds the stale claim."""
    root = _tree(tmp_path)
    before = _snapshot(root)
    code = main(["propose", str(root), "--ghost-root", str(ghost_root()), "--scope", "documentation"])
    report = json.loads(capsys.readouterr().out)
    assert code == EXIT_PROPOSED, report
    assert report["proposal"]["affected_files"] == ["README.md"]
    assert _snapshot(root) == before
