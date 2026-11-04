"""Shared helpers for the tests that use the real Ghost scan and the real Warden loop."""

from __future__ import annotations

import contextlib
import io
import json
import os
import subprocess
from pathlib import Path

import pytest

#: The same switches Warden gives Ghost when it observes a target.
GHOST_ARGS = ["--json", "--single-repo", "--no-tests", "--no-secrets", "--no-ledger",
              "--no-structure", "--no-project", "--no-correlate"]


def ghost_root() -> Path:
    """The folder that holds the `ghost_buster` package, or skip the test."""
    module = pytest.importorskip(
        "ghost_buster",
        reason="the real Ghost scan needs ghost_buster on PYTHONPATH (github.com/wking53214/ghost_tools)")
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


def sibling(name: str) -> Path:
    """A sibling checkout of the circuit (SWIZZLE, ASSAY), or skip. CIRCUIT_ROOT overrides the folder.

    The folder name is matched without regard to case (`swizzle`, `SWIZZLE`), the same rule
    `warden tagteam --stack` uses, so a clone named either way is found.
    """
    base = Path(os.environ.get("CIRCUIT_ROOT") or Path(__file__).resolve().parents[2])
    found = [p for p in base.iterdir() if p.is_dir() and p.name.lower() == name.lower()] if base.is_dir() else []
    if len(found) != 1:
        pytest.skip(f"the full gate needs the {name} checkout beside this one (or set CIRCUIT_ROOT)")
    return found[0]


def full_gate_kwargs() -> dict:
    """The complete Warden gate: real Ghost, real SWIZZLE and ASSAY, and the real Judge.

    Only a run with every check measured can end in a plain ACCEPT. Anything less is
    ACCEPT_UNVERIFIED, and Warden puts the edit back.
    """
    seat = pytest.importorskip("judge.seat", reason="the full gate needs the Judge")
    return {"ghost_tools_root": ghost_root(), "swizzle_root": sibling("swizzle"),
            "assay_root": sibling("assay"), "judge": seat.Judge()}


def init_repo(root: Path) -> None:
    """Make `root` a git repo with everything committed. Warden judges a change against a clean, tracked tree."""
    def git(*args):
        subprocess.run(["git", "-C", str(root), "-c", "user.name=test", "-c", "user.email=test@example.com",
                        *args], check=True, capture_output=True)
    git("init", "-q")
    git("add", "-A")
    git("commit", "-q", "-m", "base")


def run_loop(target: Path, scope: str = "code"):
    """The real Warden loop around the real Drafter, with the real Ghost, SWIZZLE, ASSAY and Judge."""
    pytest.importorskip("warden.tagteam", reason="needs Warden")
    from warden.authorization import grant
    from warden.tagteam import TagTeam

    from drafter import Drafter

    init_repo(Path(target))
    auth = grant("william", "transform", str(Path(target).resolve()), scope, "test")
    drafter = Drafter()
    result = TagTeam(drafter=drafter, **full_gate_kwargs()).run(target, authorization=auth)
    return result, drafter


BOM = chr(0xFEFF)


def dead_finding(file="m.py", name="orphan", kind="function", start=5, end=6, hook="no", fid="ghost-dead1"):
    """A dead_code finding in Ghost's JSON shape."""
    return {"id": fid, "severity": "minor", "status": "confirmed", "summary": "unused",
            "detector": "dead_code",
            "attributes": {"name": name, "kind": kind, "line_start": str(start),
                           "line_end": str(end), "framework_hook": hook, "dynamic_lookup_possible": "no"},
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
