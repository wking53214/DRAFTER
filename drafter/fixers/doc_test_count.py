"""Ghost's `doc_test_count_drift`: a document claims N tests and the suite has grown past it.

Every number used here comes from Ghost's finding (the claim, the lower bound on
the real count, the line, and whether Ghost judged the sentence safe to edit).
The Drafter counts nothing itself.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Optional

from warden.models import Defect, FileEdit

#: A list bullet, quote mark or numbered-list marker is kept as it is.
_MARKER = re.compile(r"^\s*(?:[-*>]\s+|\d+\.\s+)?")
#: Lines whose structure a one-sentence rewrite would damage.
_STRUCTURAL = re.compile(r"^\s*(?:\||#|```|<)")


def fix_doc_test_count(target: Path, defect: Defect) -> Optional[FileEdit]:
    attrs = defect.attributes
    if attrs.get("writable") != "yes" or not defect.file or not defect.line:
        return None
    try:
        documented, lower_bound = int(attrs["documented_count"]), int(attrs["static_lower_bound"])
    except (KeyError, ValueError):
        return None
    path = _inside(target, defect.file)
    if path is None or not path.is_file() or path.suffix.lower() != ".md":
        return None
    text = path.read_text(encoding="utf-8")
    lines = text.split("\n")
    index = defect.line - 1
    if not 0 <= index < len(lines) or _STRUCTURAL.match(lines[index]):
        return None
    sentence = re.compile(rf"[^.\n]*?\b{documented}\s+tests?\b[^.\n]*\.?")
    marker = _MARKER.match(lines[index]).group(0)
    body = lines[index][len(marker):]
    match = sentence.search(body)
    if match is None:
        return None
    lead = re.match(r"\s*", match.group(0)).group(0)
    honest = (f"{lead}The suite holds at least {lower_bound} `test_*` functions "
              f"(an earlier version of this document gave {documented}).")
    lines[index] = marker + body[:match.start()] + honest + body[match.end():]
    new = "\n".join(lines)
    return FileEdit(path=str(path.relative_to(target)), kind="write", new=new, old=text)


def _inside(target: Path, file: str) -> Optional[Path]:
    """The finding's file, only if it really lies inside the target."""
    candidate = Path(file)
    candidate = (candidate if candidate.is_absolute() else target / candidate).resolve()
    return candidate if candidate.is_relative_to(target) else None
