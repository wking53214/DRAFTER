"""The Drafter's seat in Warden's loop: one finding in, one proposed change out."""

from __future__ import annotations

import inspect
import logging
from pathlib import Path
from typing import Any, Callable, Mapping, Optional, Sequence

from cns.defect import Defect
from cns.seat import FileEdit
from warden.models import Transformation, TransformationStatus, defects_from_ghost

from ._safe import brief, finding_id, internal_error_reason
from .fixers import FIXERS

log = logging.getLogger(__name__)

#: A fixer takes the target and one finding and returns the edit that closes it,
#: or None when it cannot do so safely. It never writes. A fixer may take a third
#: argument, a function it calls with the plain-language reason whenever it refuses.
Fixer = Callable[..., Optional[FileEdit]]


def _record_id(item: Mapping[Any, Any]) -> str:
    """The `id` of a raw record that could not be turned into a finding, or '?' when it has no readable one.

    Only plain text or a whole number counts; anything else (a missing key, null, a list, a float, a boolean) is
    not an identity. A record whose own lookup raises is '?' too: this runs inside the boundary that must not crash.
    """
    try:
        raw = item.get("id")
        if isinstance(raw, bool) or not isinstance(raw, (str, int)) or raw == "":
            return "?"
        return str(raw)[:120]
    except Exception:  # noqa: BLE001 - boundary: a hostile mapping may raise anything
        return "?"


class Drafter:
    """Walks Ghost's findings in order and proposes the first fix it can make safely.

    One intentional change per call. Warden applies it, Ghost re-inspects, and
    the loop calls again. When no finding has a safe fix, `propose` returns None,
    which is how the Drafter says it has nothing left. That is not a claim that
    the tree is clean; Ghost may still report findings no fixer here handles.

    Safe, and never silent about a surprise: odd input (a file that is not
    UTF-8, a missing field, a finding that is not a finding) never raises. It
    produces no proposal and a reason. A reason that begins "internal error"
    means something other than a deliberate refusal went wrong (a bug in the
    Drafter, in a custom fixer, or in the Warden it runs with); the same event
    is logged at WARNING on the `drafter` logger, with its traceback at DEBUG.

    The Drafter keeps no memory between calls, so the same input always gives
    the same answer.

    `last_skipped` lists, for the latest `propose` call, every finding the
    Drafter recognised but would not (or could not) act on, as
    `(finding id, reason)`. A finding of a kind it has no fixer for is not
    listed; it was never its business. A record that names no kind at all (no
    usable `detector`) is listed, so that it cannot pass for a clean tree.
    Warden reads `describe_skipped()` after every call and prints it as
    `drafter_skipped`; `drafter propose` prints it too.
    """

    #: The seat contract this Drafter was written against. Warden warns when it is missing and refuses a mismatch.
    requires_contract = "1"

    #: What each built-in fixer's proposal touches, known without reading any file.
    SCOPES = {"doc_test_count_drift": "documentation", "dead_code": "code", "list_membership_in_loop": "code"}

    def __init__(self, fixers: Optional[dict[str, Fixer]] = None, scope: Optional[str] = None) -> None:
        self.fixers = dict(FIXERS if fixers is None else fixers)
        self.last_skipped: list[tuple[str, str]] = []
        #: The scope the caller is authorised for ("code" or "documentation"), if it says. When set, findings
        #: whose fix lies outside it are skipped without reading any file, and in-scope findings are tried
        #: first. When None, findings are tried in the order given, as before.
        self.scope = scope

    def scope_of(self, item: Any) -> Optional[str]:
        """Which scope a finding's fix would need ("code" or "documentation"), or None if unknown.

        Cheap: it looks at the detector name only. Every proposal carries the same answer as `scope_hint`.
        """
        detector = item.get("detector") if isinstance(item, Mapping) else getattr(item, "detector", None)
        return self.SCOPES.get(detector) if isinstance(detector, str) else None

    def describe_skipped(self) -> tuple[str, ...]:
        """`last_skipped` as one readable line each, for a caller that wants to print it."""
        return tuple(f"skipped {fid}: {reason}" for fid, reason in self.last_skipped)

    def propose(self, target: Path, observed: Sequence[Defect], baseline: str) -> Optional[Transformation]:
        self.last_skipped = []
        try:
            root = Path(target).resolve()
        except (TypeError, ValueError, OSError):
            self._skip("?", "the target path could not be used")
            return None
        if not root.is_dir():
            self._skip("?", "the target is not a folder")
            return None
        try:
            items = tuple(observed or ())
        except TypeError:
            self._skip("?", "the findings were not a list")
            return None
        for item in self._in_priority_order(items):
            defect = self._as_defect(item)
            if defect is None:
                continue
            detector = getattr(defect, "detector", None)
            fixer = self.fixers.get(detector) if isinstance(detector, str) else None
            if fixer is None:
                if not (isinstance(detector, str) and detector):
                    # A finding of a kind with no fixer is not Drafter's business and is not listed. A record that
                    # names no kind at all is different: say so, or the report cannot tell it from a clean tree.
                    self._skip(finding_id(defect), "the finding names no detector (it is missing, empty or not text), "
                                                   "so Drafter cannot tell what kind of finding it is")
                continue
            fid = finding_id(defect)
            hint = self.scope_of(defect)
            if self.scope and hint and hint != self.scope:
                self._skip(fid, f"its fix needs {hint} scope and this run allows {self.scope}")
                continue
            mark = len(self.last_skipped)
            edit = self._call(fixer, root, defect, fid)
            if not isinstance(edit, FileEdit) or not isinstance(edit.path, str):
                if len(self.last_skipped) == mark:
                    self._skip(fid, "no safe fix for this finding")
                continue
            return self._wrap(root, defect, edit, baseline, fid)
        return None

    # -- internals ---------------------------------------------------------

    def _in_priority_order(self, items: Sequence[Any]) -> list[Any]:
        """In-scope findings first (stable), when the scope is known; otherwise the order given."""
        if not self.scope:
            return list(items)
        return sorted(items, key=lambda i: 0 if self.scope_of(i) in (self.scope, None) else 1)

    def _skip(self, fid: str, reason: str) -> None:
        self.last_skipped.append((fid, reason))

    def _as_defect(self, item: Any) -> Optional[Defect]:
        if isinstance(item, Defect):
            return item
        if isinstance(item, Mapping):          # a raw Ghost finding
            try:
                defect: Defect = defects_from_ghost([item])[0]
                return defect
            except (AttributeError, IndexError, KeyError, TypeError, ValueError) as err:
                # The shapes a malformed finding can take: a field of the wrong type, a missing mapping.
                fid = _record_id(item)
                log.warning("a finding (%s) could not be read (%s: %s)", fid, type(err).__name__, brief(err))
                self._skip(fid, f"a finding could not be read ({type(err).__name__}: {brief(err)})")
                return None
            except Exception as err:  # noqa: BLE001 - boundary: a hostile mapping may raise anything
                self._internal(_record_id(item), "reading a finding", err)
                return None
        self._skip("?", f"an item that is not a finding ({type(item).__name__}) was ignored")
        return None

    def _call(self, fixer: Fixer, root: Path, defect: Defect, fid: str) -> Optional[FileEdit]:
        def sink(reason: str) -> None:
            self._skip(fid, reason)

        try:
            if _takes_reason(fixer):
                return fixer(root, defect, sink)
            return fixer(root, defect)
        except Exception as err:  # noqa: BLE001 - boundary: a fixer is pluggable code, and may fail in any way
            self._internal(fid, "a fixer", err)
            return None

    def _internal(self, fid: str, where: str, err: BaseException) -> None:
        """Record a surprise: the reason for Warden, a WARNING for the log, the traceback at DEBUG."""
        log.warning("unexpected %s in %s for finding %s: %s", type(err).__name__, where, fid, brief(err))
        log.debug("traceback for the unexpected error in %s", where, exc_info=True)
        self._skip(fid, internal_error_reason(err))

    def _wrap(self, root: Path, defect: Defect, edit: FileEdit, baseline: str, fid: str) -> Optional[Transformation]:
        try:
            code = edit.path.endswith(".py")
            proposal = Transformation(
                target=str(root),
                intent=f"close Ghost finding {defect.identity} ({defect.detector})",
                architectural_reason=defect.summary,
                affected_files=(edit.path,),
                expected_behavior=("code is taken out; Warden comments it out, never deletes, "
                                   "and only after it passes its keep and comment-out tests"
                                   if code else "documentation only; no source behavior changes"),
                preservation_requirements=(("the suite stays green", "nothing runs the removed code")
                                           if code else ("no .py file is edited",)),
                known_defects=(defect,),
                transformation_scope="code" if code else "documentation",
                baseline_reference=baseline,
                evidence=(defect.identity,),
                edits=(edit,),
                status=TransformationStatus.PROPOSED,
            )
            proposal.scope_hint = proposal.transformation_scope     # a cheap read for the caller
            return proposal
        except (AttributeError, TypeError, ValueError) as err:
            # Building the proposal touches only Warden's data shapes. A failure here is a mismatch between
            # this Drafter and the Warden it runs with (a renamed field, a new required one), never the
            # user's input, so it is reported as an internal error. Anything else propagates.
            self._internal(fid, "building the proposal", err)
            return None


def _takes_reason(fixer: Fixer) -> bool:
    try:
        params = inspect.signature(fixer).parameters.values()
    except (TypeError, ValueError):
        return False
    positional = [p for p in params if p.kind in (p.POSITIONAL_ONLY, p.POSITIONAL_OR_KEYWORD)]
    return len(positional) >= 3 or any(p.kind is p.VAR_POSITIONAL for p in params)
