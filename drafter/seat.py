"""The Drafter's seat in Warden's loop: one finding in, one proposed change out."""

from __future__ import annotations

import inspect
from pathlib import Path
from typing import Any, Callable, Mapping, Optional, Sequence

from warden.models import Defect, FileEdit, Transformation, TransformationStatus, defects_from_ghost

from ._safe import finding_id
from .fixers import FIXERS

#: A fixer takes the target and one finding and returns the edit that closes it,
#: or None when it cannot do so safely. It never writes. A fixer may take a third
#: argument, a function it calls with the plain-language reason whenever it refuses.
Fixer = Callable[..., Optional[FileEdit]]


class Drafter:
    """Walks Ghost's findings in order and proposes the first fix it can make safely.

    One intentional change per call. Warden applies it, Ghost re-inspects, and
    the loop calls again. When no finding has a safe fix, `propose` returns None,
    which is how the Drafter says it has nothing left. That is not a claim that
    the tree is clean; Ghost may still report findings no fixer here handles.

    Safe or silent: odd input (a file that is not UTF-8, a missing field, a
    finding that is not a finding) never raises. It produces no proposal.

    The Drafter keeps no memory between calls, so the same input always gives
    the same answer.

    `last_skipped` lists, for the latest `propose` call, every finding the
    Drafter recognised but would not (or could not) act on, as
    `(finding id, reason)`. A finding of a kind it has no fixer for is not
    listed; it was never its business. Warden's Drafter protocol has no channel
    for notes, so nothing prints this today; a caller can read it after the run.
    """

    #: The seat contract this Drafter was written against. Warden warns when it is missing and refuses a mismatch.
    requires_contract = "1"

    def __init__(self, fixers: Optional[dict[str, Fixer]] = None) -> None:
        self.fixers = dict(FIXERS if fixers is None else fixers)
        self.last_skipped: list[tuple[str, str]] = []

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
        for item in items:
            defect = self._as_defect(item)
            if defect is None:
                continue
            detector = getattr(defect, "detector", None)
            fixer = self.fixers.get(detector) if isinstance(detector, str) else None
            if fixer is None:
                continue
            fid = finding_id(defect)
            mark = len(self.last_skipped)
            edit = self._call(fixer, root, defect, fid)
            if not isinstance(edit, FileEdit) or not isinstance(edit.path, str):
                if len(self.last_skipped) == mark:
                    self._skip(fid, "no safe fix for this finding")
                continue
            return self._wrap(root, defect, edit, baseline, fid)
        return None

    # -- internals ---------------------------------------------------------

    def _skip(self, fid: str, reason: str) -> None:
        self.last_skipped.append((fid, reason))

    def _as_defect(self, item: Any) -> Optional[Defect]:
        if isinstance(item, Defect):
            return item
        if isinstance(item, Mapping):          # a raw Ghost finding
            try:
                return defects_from_ghost([item])[0]
            except Exception:  # noqa: BLE001 - safe or silent
                self._skip("?", "a finding could not be read")
                return None
        self._skip("?", f"an item that is not a finding ({type(item).__name__}) was ignored")
        return None

    def _call(self, fixer: Fixer, root: Path, defect: Defect, fid: str) -> Optional[FileEdit]:
        sink = lambda reason: self._skip(fid, reason)  # noqa: E731
        try:
            if _takes_reason(fixer):
                return fixer(root, defect, sink)
            return fixer(root, defect)
        except Exception as err:  # noqa: BLE001 - safe or silent
            self._skip(fid, f"the fixer failed with {type(err).__name__}")
            return None

    def _wrap(self, root: Path, defect: Defect, edit: FileEdit, baseline: str, fid: str) -> Optional[Transformation]:
        try:
            code = edit.path.endswith(".py")
            return Transformation(
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
        except Exception as err:  # noqa: BLE001 - safe or silent
            self._skip(fid, f"the proposal could not be built ({type(err).__name__})")
            return None


def _takes_reason(fixer: Fixer) -> bool:
    try:
        params = inspect.signature(fixer).parameters.values()
    except (TypeError, ValueError):
        return False
    positional = [p for p in params if p.kind in (p.POSITIONAL_ONLY, p.POSITIONAL_OR_KEYWORD)]
    return len(positional) >= 3 or any(p.kind is p.VAR_POSITIONAL for p in params)
