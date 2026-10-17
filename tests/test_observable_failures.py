"""A real bug is observable. It is never swallowed into a quiet "no safe fix".

A deliberate refusal is ordinary: a reason, DEBUG at most. A surprise (an exception nobody meant to raise)
reaches a person two ways: the reason string starts "internal error" and names the exception, which is
what Warden prints as `drafter_skipped`; and the `drafter` logger records a WARNING with the traceback at DEBUG.
"""

import logging

import pytest

from drafter import Drafter
from support import dead_finding, doc_finding, propose

README = "# T\n\nThe suite is healthy: 16 tests passed.\n"
SRC = "def used():\n    return 1\n\n\ndef orphan():\n    return 2\n"


def _root(tmp_path):
    root = tmp_path / "tgt"
    root.mkdir()
    (root / "README.md").write_text(README, encoding="utf-8")
    (root / "m.py").write_text(SRC, encoding="utf-8")
    return root


def _boom(*_args, **_kwargs):
    raise RuntimeError("injected bug")


def _warnings(caplog):
    return [r for r in caplog.records if r.levelno >= logging.WARNING and r.name.startswith("drafter")]


def _assert_observable(drafter, caplog, where):
    ((_, reason),) = drafter.last_skipped
    assert reason.startswith("internal error (RuntimeError: injected bug)"), reason
    assert drafter.describe_skipped()[0].endswith(reason)               # what Warden prints as drafter_skipped
    (warning,) = _warnings(caplog)
    assert warning.levelno == logging.WARNING
    assert "RuntimeError" in warning.getMessage() and "injected bug" in warning.getMessage()
    assert where in warning.getMessage() or where == ""
    traces = [r for r in caplog.records if r.levelno == logging.DEBUG and r.exc_info]
    assert traces and traces[0].exc_info[0] is RuntimeError                # traceback at DEBUG, not WARNING
    assert warning.exc_info is None


@pytest.mark.parametrize("module, finding", [
    ("drafter.fixers.doc_test_count", lambda: doc_finding()),
    ("drafter.fixers.dead_code", lambda: dead_finding(start=5, end=6)),
    ("drafter.fixers.list_membership", lambda: {
        "id": "ghost-l1", "severity": "minor", "status": "confirmed", "summary": "s",
        "detector": "list_membership_in_loop",
        "attributes": {"name": "X", "container": "list", "defined_at": "1"},
        "evidence": {"file": "m.py", "line_start": 1}}),
])
def test_a_bug_inside_a_built_in_fixer_is_reported_not_swallowed(tmp_path, monkeypatch, caplog, module, finding):
    monkeypatch.setattr(f"{module}._fix", _boom)
    caplog.set_level(logging.DEBUG, logger="drafter")
    proposal, drafter = propose(_root(tmp_path), finding())
    assert proposal is None
    _assert_observable(drafter, caplog, "fixer")


def test_a_bug_inside_a_custom_fixer_is_reported_not_swallowed(tmp_path, caplog):
    caplog.set_level(logging.DEBUG, logger="drafter")
    drafter = Drafter(fixers={"dead_code": _boom})
    from warden.models import defects_from_ghost
    assert drafter.propose(_root(tmp_path), defects_from_ghost([dead_finding()]), "base") is None
    _assert_observable(drafter, caplog, "a fixer")


def test_a_bug_while_reading_a_finding_is_reported(tmp_path, monkeypatch, caplog):
    monkeypatch.setattr("drafter.seat.defects_from_ghost", _boom)
    caplog.set_level(logging.DEBUG, logger="drafter")
    drafter = Drafter()
    assert drafter.propose(_root(tmp_path), [doc_finding()], "base") is None      # a raw Ghost finding
    _assert_observable(drafter, caplog, "reading a finding")


def test_a_malformed_finding_says_what_was_wrong(tmp_path, caplog):
    bad = doc_finding()
    bad["attributes"] = 5                                   # dict(5) raises TypeError
    drafter = Drafter()
    assert drafter.propose(_root(tmp_path), [bad], "base") is None
    ((_, reason),) = drafter.last_skipped
    assert reason.startswith("a finding could not be read (TypeError")
    assert [r.levelno for r in _warnings(caplog)] == [logging.WARNING]


def test_a_mismatch_with_warden_when_building_the_proposal_is_reported(tmp_path, monkeypatch, caplog):
    def renamed_field(**_kwargs):
        raise TypeError("Transformation() got an unexpected keyword argument 'edits'")
    monkeypatch.setattr("drafter.seat.Transformation", renamed_field)
    caplog.set_level(logging.DEBUG, logger="drafter")
    proposal, drafter = propose(_root(tmp_path), doc_finding())
    assert proposal is None
    ((_, reason),) = drafter.last_skipped
    assert reason.startswith("internal error (TypeError: Transformation() got an unexpected keyword")
    assert len(_warnings(caplog)) == 1


def test_an_unknown_kind_of_failure_while_building_the_proposal_is_not_hidden(tmp_path, monkeypatch):
    monkeypatch.setattr("drafter.seat.Transformation", _boom)
    with pytest.raises(RuntimeError, match="injected bug"):
        propose(_root(tmp_path), doc_finding())


def test_a_finding_whose_identity_cannot_be_read_is_logged(caplog):
    from drafter._safe import finding_id

    class Hostile:
        @property
        def identity(self):
            raise RuntimeError("injected bug")

    assert finding_id(Hostile()) == "?"
    (warning,) = _warnings(caplog)
    assert "RuntimeError" in warning.getMessage()


def test_an_ordinary_refusal_is_a_reason_not_an_alarm(tmp_path, caplog):
    caplog.set_level(logging.DEBUG, logger="drafter")
    proposal, drafter = propose(_root(tmp_path), dead_finding(name="nothing_by_this_name", start=5, end=6))
    assert proposal is None and drafter.last_skipped
    assert not drafter.last_skipped[0][1].startswith("internal error")
    assert _warnings(caplog) == []
    assert any(r.levelno == logging.DEBUG and "refused" in r.getMessage() for r in caplog.records)


def test_the_library_never_configures_logging():
    names = {type(h).__name__ for h in logging.getLogger("drafter").handlers}
    assert names == {"NullHandler"} or names <= {"NullHandler", "LogCaptureHandler"}
