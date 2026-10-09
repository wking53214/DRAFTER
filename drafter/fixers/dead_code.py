"""Ghost's `dead_code`: a top-level function or class nothing references.

Every fact comes from Ghost's finding (name, kind, first and last line, whether
a framework calls it by name). The Drafter parses nothing. It proposes taking
the exact lines out; Warden decides whether that is allowed. Warden never
deletes: it comments the code out with a timestamp, and only after the code
has passed a keep test and a comment-out test.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from warden.models import Defect, FileEdit

_KEYWORD = {"function": ("def ", "async def "), "class": ("class ",)}


def fix_dead_code(target: Path, defect: Defect) -> Optional[FileEdit]:
    attrs = defect.attributes
    if attrs.get("framework_hook") != "no" or not defect.file:
        return None
    name, kind = attrs.get("name"), attrs.get("kind")
    try:
        start, end = int(attrs["line_start"]), int(attrs["line_end"])
    except (KeyError, ValueError):
        return None
    if not name or kind not in _KEYWORD or not 1 <= start <= end:
        return None
    path = _inside(target, defect.file)
    if path is None or not path.is_file() or path.suffix != ".py":
        return None
    text = path.read_text(encoding="utf-8")
    lines = text.split("\n")
    if end > len(lines):
        return None
    block = lines[start - 1:end]
    opener = block[0]
    if not any(opener.startswith(k + name) and opener[len(k) + len(name):][:1] in {"(", ":", " "}
               for k in _KEYWORD[kind]):
        return None
    old = "\n".join(block) + "\n"
    if text.count(old) != 1:
        return None
    return FileEdit(path=str(path.relative_to(target)), kind="replace", old=old, new="")


def _inside(target: Path, file: str) -> Optional[Path]:
    """The finding's file, only if it really lies inside the target."""
    candidate = Path(file)
    candidate = (candidate if candidate.is_absolute() else target / candidate).resolve()
    return candidate if candidate.is_relative_to(target) else None
