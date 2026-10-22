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
from drafter.cli import EXIT_NO_FINDINGS, EXIT_NOTHING, EXIT_PIPE_CLOSED, EXIT_PROPOSED, EXIT_USAGE, main
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
    assert (EXIT_PROPOSED, EXIT_NOTHING, EXIT_USAGE, EXIT_NO_FINDINGS, EXIT_PIPE_CLOSED) == (0, 1, 2, 3, 4)
    doc = sys.modules["drafter.cli"].__doc__ or ""
    for code, meaning in ((0, "a proposal was made"), (1, "nothing to propose"), (2, "usage error"),
                          (3, "findings could not be obtained"), (4, "the output pipe was closed")):
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


@pytest.mark.parametrize("argv", [["propose", ".", "--finding", "f.json"], ["propose", ".", "--ghost", "g"],
                                  ["propose", ".", "--scop", "code"], ["propose", ".", "--verb"], ["--vers"]])
def test_an_abbreviated_option_is_a_usage_error_not_a_guess(argv, capsys):
    with pytest.raises(SystemExit) as stop:
        main(argv)
    assert stop.value.code == EXIT_USAGE
    assert "usage:" in capsys.readouterr().err


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


def test_a_scan_with_no_ghost_root_is_refused_by_warden_and_is_exit_3(tmp_path, capsys):
    """Warden 0.13.2 and later will not scan with no named root (an installed Ghost never stands in).

    That is exit 3, not 1.
    """
    assert main(["propose", str(_tree(tmp_path))]) == EXIT_NO_FINDINGS
    captured = capsys.readouterr()
    assert captured.out == ""
    assert "no root" in captured.err and "--ghost-root" in captured.err


def test_a_ghost_root_that_does_not_hold_the_package_is_exit_3(tmp_path, capsys):
    empty = tmp_path / "not_ghost"
    empty.mkdir()
    assert main(["propose", str(_tree(tmp_path)), "--ghost-root", str(empty)]) == EXIT_NO_FINDINGS
    assert "could not obtain findings" in capsys.readouterr().err


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


def test_an_empty_path_is_a_usage_error_not_the_current_folder(tmp_path, capsys, monkeypatch):
    """`Path("")` is the current folder, so before 0.2.9 `drafter propose ""` quietly made the working directory the
    target and printed a proposal for it."""
    root = _tree(tmp_path)
    findings = _findings(tmp_path, doc_finding(line=3))
    monkeypatch.chdir(root)
    before = _snapshot(root)
    assert main(["propose", str(root), "--findings", str(findings)]) == EXIT_PROPOSED     # the folder itself works
    capsys.readouterr()
    code = main(["propose", "", "--findings", str(findings)])
    captured = capsys.readouterr()
    assert code == EXIT_USAGE and captured.out == ""
    assert "PATH is empty" in captured.err and "Traceback" not in captured.err
    assert len(captured.err.strip().splitlines()) == 1
    assert _snapshot(root) == before


def test_python_dash_m_drafter_with_an_empty_path_exits_2(tmp_path):
    env = {**os.environ, "PYTHONPATH": os.pathsep.join([str(REPO), os.environ.get("PYTHONPATH", "")])}
    root = _tree(tmp_path)
    findings = _findings(tmp_path, doc_finding(line=3))
    done = subprocess.run([sys.executable, "-m", "drafter", "propose", "", "--findings", str(findings)],
                          capture_output=True, text=True, env=env, cwd=root, check=False)
    assert done.returncode == EXIT_USAGE and done.stdout == "", (done.stdout, done.stderr)
    assert "PATH is empty" in done.stderr


class _ClosedPipe:
    """A stdout whose reader has gone away."""

    def write(self, _text: str) -> int:
        raise BrokenPipeError(32, "Broken pipe")

    def flush(self) -> None:
        raise BrokenPipeError(32, "Broken pipe")


def test_a_closed_output_pipe_is_exit_4_with_a_message_not_a_traceback(tmp_path, capsys, monkeypatch):
    root = _tree(tmp_path)
    findings = _findings(tmp_path, doc_finding(line=3))
    monkeypatch.setattr(sys, "stdout", _ClosedPipe())
    code = main(["propose", str(root), "--findings", str(findings)])
    assert code == EXIT_PIPE_CLOSED and code not in (EXIT_NOTHING, EXIT_PROPOSED)
    err = capsys.readouterr().err
    assert "output pipe was closed" in err and "Traceback" not in err


def test_python_dash_m_drafter_into_a_closed_pipe_exits_4_cleanly(tmp_path):
    """The real thing: stdout is a pipe nobody reads, as with `drafter propose ... | head -c0`."""
    env = {**os.environ, "PYTHONPATH": os.pathsep.join([str(REPO), os.environ.get("PYTHONPATH", "")])}
    root = _tree(tmp_path)
    findings = _findings(tmp_path, doc_finding(line=3))
    read_end, write_end = os.pipe()
    os.close(read_end)                                  # every writer now gets EPIPE
    try:
        done = subprocess.run([sys.executable, "-m", "drafter", "propose", str(root), "--findings", str(findings)],
                              stdout=write_end, stderr=subprocess.PIPE, text=True, env=env, cwd=tmp_path, check=False)
    finally:
        os.close(write_end)
    assert done.returncode == EXIT_PIPE_CLOSED, done.stderr
    assert "Traceback" not in done.stderr and "BrokenPipeError" not in done.stderr
    assert "output pipe was closed" in done.stderr


class _FullDevice:
    """A stdout whose device is full: the write or the flush fails with ENOSPC, as on /dev/full."""

    def write(self, _text: str) -> int:
        raise OSError(28, "No space left on device")

    def flush(self) -> None:
        raise OSError(28, "No space left on device")


def test_a_full_stdout_is_exit_4_with_one_plain_line_not_a_traceback(tmp_path, capsys, monkeypatch):
    """Before 0.2.9 the OSError escaped as a traceback and exit 1, which reads as "nothing to propose"."""
    root = _tree(tmp_path)
    findings = _findings(tmp_path, doc_finding(line=3))
    monkeypatch.setattr(sys, "stdout", _FullDevice())
    code = main(["propose", str(root), "--findings", str(findings)])
    assert code == EXIT_PIPE_CLOSED and code not in (EXIT_NOTHING, EXIT_PROPOSED)
    err = capsys.readouterr().err
    assert "could not be written to stdout" in err and "No space left on device" in err
    assert "Traceback" not in err and len(err.strip().splitlines()) == 1


def test_a_closed_stdout_is_exit_4_with_one_plain_line_not_a_traceback(tmp_path, capsys, monkeypatch):
    """With no stdout at all (`sys.stdout` is None) the flush used to raise AttributeError, exit 1."""
    root = _tree(tmp_path)
    findings = _findings(tmp_path, doc_finding(line=3))
    monkeypatch.setattr(sys, "stdout", None)
    code = main(["propose", str(root), "--findings", str(findings)])
    assert code == EXIT_PIPE_CLOSED
    err = capsys.readouterr().err
    assert "could not be written to stdout" in err and "stdout is closed" in err
    assert "Traceback" not in err and "AttributeError" not in err and len(err.strip().splitlines()) == 1


def test_python_dash_m_drafter_with_stdout_on_a_full_device_exits_4_cleanly(tmp_path):
    """The real thing: the child's stdout is /dev/full, opened for writing (never replaced, never an --out)."""
    env = {**os.environ, "PYTHONPATH": os.pathsep.join([str(REPO), os.environ.get("PYTHONPATH", "")])}
    root = _tree(tmp_path)
    findings = _findings(tmp_path, doc_finding(line=3))
    with open("/dev/full", "wb") as full:
        done = subprocess.run([sys.executable, "-m", "drafter", "propose", str(root), "--findings", str(findings)],
                              stdout=full, stderr=subprocess.PIPE, text=True, env=env, cwd=tmp_path, check=False)
    assert done.returncode == EXIT_PIPE_CLOSED, done.stderr
    assert "Traceback" not in done.stderr and "Exception ignored" not in done.stderr
    assert "could not be written to stdout" in done.stderr and len(done.stderr.strip().splitlines()) == 1


def test_python_dash_m_drafter_with_file_descriptor_1_closed_exits_4_cleanly(tmp_path):
    """The real thing: the process starts with fd 1 closed, so `sys.stdout` is None (the report cannot go anywhere)."""
    env = {**os.environ, "PYTHONPATH": os.pathsep.join([str(REPO), os.environ.get("PYTHONPATH", "")])}
    root = _tree(tmp_path)
    findings = _findings(tmp_path, doc_finding(line=3))
    done = subprocess.run([sys.executable, "-m", "drafter", "propose", str(root), "--findings", str(findings)],
                          stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, env=env, cwd=tmp_path,
                          check=False, preexec_fn=lambda: os.close(1))
    assert done.returncode == EXIT_PIPE_CLOSED, done.stderr
    assert "Traceback" not in done.stderr and "AttributeError" not in done.stderr
    assert "could not be written to stdout" in done.stderr and len(done.stderr.strip().splitlines()) == 1


def test_the_real_ghost_scan_feeds_the_dry_run(tmp_path, capsys):
    """Integration: no --findings file, Warden's own read-only Ghost scan finds the stale claim."""
    root = _tree(tmp_path)
    before = _snapshot(root)
    code = main(["propose", str(root), "--ghost-root", str(ghost_root()), "--scope", "documentation"])
    report = json.loads(capsys.readouterr().out)
    assert code == EXIT_PROPOSED, report
    assert report["proposal"]["affected_files"] == ["README.md"]
    assert _snapshot(root) == before


# A record that cannot be acted on must say why in the report. Before 0.2.8 `[{"id":"x"}]` printed
# `"findings": 1, "proposal": null, "skipped": []` and exit 1, so the report could not say why.

NO_DETECTOR = "names no detector"


@pytest.mark.parametrize("record", [{"id": "x"}, {"id": "x", "detector": ""}, {"id": "x", "detector": None},
                                    {"id": "x", "detector": 5}, {"id": "x", "detector": ["dead_code"]}],
                         ids=["missing", "empty", "null", "number", "list"])
def test_a_record_with_no_usable_detector_is_skipped_with_a_reason(tmp_path, capsys, record):
    code = main(["propose", str(_tree(tmp_path)), "--findings", str(_findings(tmp_path, record))])
    report = json.loads(capsys.readouterr().out)
    assert code == EXIT_NOTHING                      # the exit-code table is unchanged: 1, and the JSON says why
    assert report["findings"] == 1 and report["proposal"] is None
    ((entry,),) = [report["skipped"]]
    assert entry["finding"] == "x" and NO_DETECTOR in entry["reason"]


def test_a_kind_of_finding_with_no_fixer_is_still_not_listed(tmp_path, capsys):
    """Only a record that names no kind is reported. A finding for a detector Drafter has no fixer for is not
    its business, as the README says, and stays out of `skipped`."""
    record = {"id": "x", "detector": "some_other_detector"}
    code = main(["propose", str(_tree(tmp_path)), "--findings", str(_findings(tmp_path, record))])
    report = json.loads(capsys.readouterr().out)
    assert code == EXIT_NOTHING and report["findings"] == 1 and report["skipped"] == []


@pytest.mark.parametrize("field, value", [("evidence", "not an object"), ("attributes", 3), ("evidence", ["a"])])
def test_a_record_of_the_wrong_shape_is_skipped_not_a_traceback(tmp_path, capsys, field, value):
    """Warden's reader raises on these. That used to escape as a traceback with exit 1, which reads as 'nothing
    to propose'."""
    bad = dead_finding(fid="ghost-bad")
    bad[field] = value
    code = main(["propose", str(_tree(tmp_path)), "--findings", str(_findings(tmp_path, bad))])
    captured = capsys.readouterr()
    report = json.loads(captured.out)
    assert code == EXIT_NOTHING and "Traceback" not in captured.err
    assert report["findings"] == 1 and report["proposal"] is None
    ((entry,),) = [report["skipped"]]
    assert "could not be read" in entry["reason"]


def test_a_bad_record_does_not_stop_the_good_one_after_it(tmp_path, capsys):
    bad = {"id": "bad", "detector": "doc_test_count_drift", "evidence": "not an object"}
    good = doc_finding(line=3)
    code = main(["propose", str(_tree(tmp_path)), "--findings", str(_findings(tmp_path, bad, {"id": "x"}, good))])
    report = json.loads(capsys.readouterr().out)
    assert code == EXIT_PROPOSED and report["findings"] == 3
    assert report["proposal"]["affected_files"] == ["README.md"]
    assert any("could not be read" in s["reason"] for s in report["skipped"])
    assert any(s["finding"] == "x" and NO_DETECTOR in s["reason"] for s in report["skipped"])


def test_the_exit_code_table_in_the_readme_is_the_one_the_code_has():
    """The README table must keep saying exit 1 covers a skipped finding, since a malformed record exits 1."""
    readme = (REPO / "README.md").read_text(encoding="utf-8")
    rows = dict(re.findall(r"^\| (\d) \| (.+) \|$", readme, re.MULTILINE))
    assert set(rows) == {"0", "1", "2", "3", "4"}
    assert "nothing to propose" in rows["1"] and "why findings were skipped" in rows["1"]


def test_the_readme_exit_4_row_covers_a_full_or_closed_stdout():
    """Exit 4 is "the report was not delivered": a closed pipe, a full device and a closed stdout all land there."""
    readme = (REPO / "README.md").read_text(encoding="utf-8")
    row = dict(re.findall(r"^\| (\d) \| (.+) \|$", readme, re.MULTILINE))["4"]
    assert "pipe was closed" in row and "full device" in row and "no stdout" in row
    assert 'never "nothing to propose"' in row
    doc = sys.modules["drafter.cli"].__doc__ or ""
    assert "a full device" in doc and "no stdout at all" in doc


def test_the_readme_exit_2_row_names_an_empty_path():
    readme = (REPO / "README.md").read_text(encoding="utf-8")
    assert "PATH is empty" in dict(re.findall(r"^\| (\d) \| (.+) \|$", readme, re.MULTILINE))["2"]
    assert "PATH is empty" in (sys.modules["drafter.cli"].__doc__ or "")
