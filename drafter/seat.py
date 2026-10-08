"""The Drafter's seat in Warden's loop: one finding in, one proposed change out."""

from __future__ import annotations

from pathlib import Path
from typing import Callable, Optional, Sequence

from warden.models import Defect, FileEdit, Transformation, TransformationStatus

from .fixers import FIXERS

#: A fixer takes one finding and returns the edit that closes it, or None when
#: it cannot do so safely. It never writes.
Fixer = Callable[[Path, Defect], Optional[FileEdit]]


class Drafter:
    """Walks Ghost's findings in order and proposes the first fix it can make safely.

    One intentional change per call. Warden applies it, Ghost re-inspects, and
    the loop calls again. When no finding has a safe fix, `propose` returns None,
    which is how the Drafter says it has nothing left. That is not a claim that
    the tree is clean; Ghost may still report findings no fixer here handles.
    """

    def __init__(self, fixers: Optional[dict[str, Fixer]] = None) -> None:
        self.fixers = dict(FIXERS if fixers is None else fixers)

    def propose(self, target: Path, observed: Sequence[Defect], baseline: str) -> Optional[Transformation]:
        target = Path(target).resolve()
        for defect in observed:
            fixer = self.fixers.get(defect.detector or "")
            if fixer is None:
                continue
            edit = fixer(target, defect)
            if edit is None:
                continue
            return Transformation(
                target=str(target),
                intent=f"close Ghost finding {defect.identity} ({defect.detector})",
                architectural_reason=defect.summary,
                affected_files=(edit.path,),
                expected_behavior="documentation only; no source behavior changes",
                preservation_requirements=("no .py file is edited",),
                known_defects=(defect,),
                transformation_scope="documentation",
                baseline_reference=baseline,
                evidence=(defect.identity,),
                edits=(edit,),
                status=TransformationStatus.PROPOSED,
            )
        return None
