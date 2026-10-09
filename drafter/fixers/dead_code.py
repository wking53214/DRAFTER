"""Ghost's `dead_code`: a top-level function or class nothing references.

Ghost supplies the facts (name, kind, first and last line, whether a framework
calls it by name). The Drafter does not parse the file with a real parser. It
checks, by plain text, that the span Ghost named is exactly one top-level
definition (see `drafter._pyblock`), takes any decorators directly above it
along with it, and proposes taking those exact lines out. Anything that does
not line up is refused with a recorded reason. Warden decides whether the
removal is allowed: it never deletes, it comments the code out with a
timestamp, and only after the code has passed a keep test and a comment-out
test.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from warden.models import Defect, FileEdit

from .._pyblock import find_block
from .._safe import (Reason, attributes_of, check_editable, read_source, refuse,
                     resolve_in_target, run_fixer, split_lines, whole_int)

_KINDS = {"function", "class"}


def fix_dead_code(target: Path, defect: Defect, why: Optional[Reason] = None) -> Optional[FileEdit]:
    return run_fixer(lambda: _fix(target, defect), why)


def _fix(target: Path, defect: Defect) -> FileEdit:
    attrs = attributes_of(defect)
    hook = attrs.get("framework_hook")
    if hook != "no":
        refuse(f"Ghost does not say 'framework_hook: no' (it says {hook!r}), so a framework may call it")
    name, kind = attrs.get("name"), attrs.get("kind")
    if not isinstance(name, str) or not name.isidentifier() or not name.isascii():
        refuse(f"the finding's name {name!r} is not a plain identifier")
    if kind not in _KINDS:
        refuse(f"the finding's kind {kind!r} is neither function nor class")
    start = whole_int(attrs.get("line_start"), "line_start")
    end = whole_int(attrs.get("line_end"), "line_end")
    path, rel = resolve_in_target(target, getattr(defect, "file", None))
    if path.suffix != ".py":
        refuse(f"{rel.as_posix()} is not a .py file")
    check_editable(rel)
    text = read_source(path)
    body = text[1:] if text.startswith("\ufeff") else text      # the BOM is never part of an edit
    rows = split_lines(body)
    first, last = find_block(tuple(r[0] for r in rows), name, kind, start, end)
    old = "".join(content + ending for content, ending in rows[first:last + 1])
    if body.count(old) != 1:
        refuse(f"the lines to remove appear {body.count(old)} times in the file")
    return FileEdit(path=rel.as_posix(), kind="replace", old=old, new="")
