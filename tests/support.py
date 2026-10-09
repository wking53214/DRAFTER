"""Shared helpers for the tests that use the real Ghost scan and the real Warden loop."""

from __future__ import annotations

import contextlib
import io
import json
from pathlib import Path

import pytest

#: The same switches Warden gives Ghost when it observes a target.
GHOST_ARGS = ["--json", "--single-repo", "--no-tests", "--no-secrets", "--no-ledger",
              "--no-structure", "--no-project", "--no-correlate"]


def ghost_root() -> Path:
    """The folder that holds the `ghost_buster` package, or skip the test."""
    module = pytest.importorskip(
        "ghost_buster", reason="the real Ghost scan needs ghost_buster on PYTHONPATH (github.com/wking53214/ghost_tools)")
    return Path(module.__file__).resolve().parent.parent


def real_findings(target: Path) -> list[dict]:
    """What the real Ghost reports for `target`: raw findings, exactly as Warden would read them."""
    cli = pytest.importorskip("ghost_buster.cli", reason="the real Ghost scan needs ghost_buster")
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        cli.main([str(Path(target).resolve()), *GHOST_ARGS])
    data = json.loads(out.getvalue())
    return list(data["findings"] if isinstance(data, dict) else data)


def many_tests(count: int = 40) -> str:
    """A test module with `count` tiny tests, so a README claiming fewer is stale."""
    return "".join(f"def test_case_{i}():\n    assert True\n\n" for i in range(count))


def run_loop(target: Path, scope: str = "code"):
    """The real Warden loop around the real Drafter, with the real Ghost re-inspecting."""
    pytest.importorskip("warden.tagteam", reason="needs Warden")
    from warden.authorization import grant
    from warden.tagteam import TagTeam

    from drafter import Drafter

    auth = grant("william", "transform", str(Path(target).resolve()), scope, "test")
    drafter = Drafter()
    result = TagTeam(drafter=drafter, ghost_tools_root=ghost_root()).run(target, authorization=auth)
    return result, drafter


BOM = chr(0xFEFF)


def dead_finding(file="m.py", name="orphan", kind="function", start=5, end=6, hook="no", fid="ghost-dead1"):
    """A dead_code finding in Ghost's JSON shape."""
    return {"id": fid, "severity": "minor", "status": "confirmed", "summary": "unused",
            "detector": "dead_code",
            "attributes": {"name": name, "kind": kind, "line_start": str(start),
                           "line_end": str(end), "framework_hook": hook},
            "evidence": {"file": file, "line_start": start, "line_end": end}}


def doc_finding(file="README.md", line=3, documented=16, lower=79, writable="yes", fid="ghost-doc1"):
    """A doc_test_count_drift finding in Ghost's JSON shape."""
    return {"id": fid, "severity": "minor", "status": "confirmed", "summary": "stale count",
            "detector": "doc_test_count_drift",
            "attributes": {"documented_count": str(documented), "static_lower_bound": str(lower),
                           "writable": writable},
            "evidence": {"file": file, "line_start": line}}


def propose(root, *findings):
    """Run a fresh Drafter on raw Ghost findings. Returns (proposal or None, the drafter)."""
    from warden.models import defects_from_ghost

    from drafter import Drafter

    drafter = Drafter()
    return drafter.propose(root, defects_from_ghost(list(findings)), "base"), drafter
