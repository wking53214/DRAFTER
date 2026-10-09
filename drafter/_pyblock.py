"""A small, local, text-level check that a line range is exactly one top-level def or class.

The Drafter may not import `ast`, so this reads the file as text. It is a first
line of defence, not the last: Warden's keep test and comment-out test remain
the real gate. It is deliberately stricter than Python: anything irregular is a
refusal, never a guess.

What it checks, for a finding that says "function/class NAME spans lines A to B":

* line A starts, at column 0, with `def NAME`, `async def NAME` or `class NAME`;
* the block really runs from there through every following line that is blank,
  indented, or a continuation of a bracket or string, and its last line of code
  is line B (Ghost's end and the text must agree);
* the header ends with a colon, so there is no body on the same line;
* decorators sitting directly above are part of the block (so none is stranded);
* nothing irregular: no tab and space indentation mixed, no backslash line
  continuation, no multi-line string with text at column 0, no second
  definition of the same name, no `@NAME` use elsewhere.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Sequence

from ._safe import refuse


@dataclass
class _Line:
    blank: bool = False
    cont: bool = False             # starts inside a bracket, a string or after a backslash
    in_string: bool = False        # starts inside a string
    comment_only: bool = False
    code: str = ""                 # the line's code, strings blanked out, comment dropped
    start: int = 0                 # first physical line of the statement this line is in
    clean_end: bool = True         # nothing left open at the end of this line
    bad: bool = False              # e.g. a one-quote string that never closes


def scan(lines: Sequence[str]) -> list[_Line]:
    """Walk the lines once, tracking strings, brackets and comments."""
    out: list[_Line] = []
    depth = 0
    quote = ""            # the open string's quote text ('"', "'", '\"\"\"' ...), or ""
    backslash = False
    for i, line in enumerate(lines):
        info = _Line(blank=not line.strip())
        info.cont = bool(quote) or depth > 0 or backslash
        info.in_string = bool(quote)
        info.start = out[i - 1].start if (info.cont and i) else i
        info.comment_only = (not info.cont) and line.lstrip().startswith("#")
        backslash = False
        code: list[str] = []
        j, n = 0, len(line)
        escaped_eol = False
        while j < n:
            c = line[j]
            if quote:
                if c == "\\":
                    if j + 1 >= n:
                        escaped_eol = True
                    j += 2
                    continue
                if line.startswith(quote, j):
                    j += len(quote)
                    quote = ""
                    continue
                j += 1
                continue
            if c == "#":
                break
            if c in "\"'":
                quote = c * 3 if line.startswith(c * 3, j) else c
                j += len(quote)
                code.append("S")
                continue
            if c in "([{":
                depth += 1
            elif c in ")]}":
                depth = max(0, depth - 1)
            elif c == "\\" and j == n - 1:
                backslash = True
                j += 1
                continue
            code.append(c)
            j += 1
        if quote and len(quote) == 1 and not escaped_eol:
            info.bad = True           # a one-quote string cannot run past its line
            quote = ""
        info.code = "".join(code).rstrip()
        info.clean_end = depth == 0 and not quote and not backslash
        out.append(info)
    return out


_OPENER = re.compile(r"(async def |def |class )")


def find_block(lines: Sequence[str], name: str, kind: str, start: int, end: int) -> tuple[int, int]:
    """(first, last) zero-based line numbers to remove: decorators plus the def or class."""
    n = len(lines)
    if not 1 <= start <= end <= n:
        refuse(f"lines {start}-{end} are outside the file ({n} lines)")
    d = start - 1
    info = scan(lines)
    if info[d].cont:
        refuse(f"line {start} sits inside a string or bracket, not at the start of a statement")
    opener = _OPENER.match(lines[d])
    if opener is None or not lines[d].startswith(opener.group(1) + name):
        refuse(f"line {start} does not start with 'def {name}' / 'class {name}' at column 0")
    keyword = opener.group(1).strip()
    if (kind == "class") != (keyword == "class") or kind not in {"function", "class"}:
        refuse(f"line {start} is a '{keyword}', but Ghost says {kind}")
    after = lines[d][len(opener.group(1) + name):][:1]
    if after not in {"(", ":", "[", " "}:
        refuse(f"line {start}: the name is longer than '{name}'")

    # The header may run over several lines; it must end with a colon and nothing after it.
    header_last = d
    while header_last + 1 < n and info[header_last + 1].start == d:
        header_last += 1
    if not info[header_last].code.endswith(":") or not info[header_last].clean_end:
        refuse(f"'{name}' has its body on the header line or an unusual header")

    # The body: blank, indented, or continuation lines. The first statement at column 0 ends it.
    j, last = header_last + 1, None
    while j < n:
        text, here = lines[j], info[j]
        if here.blank:
            j += 1
            continue
        if here.cont:
            if here.in_string and text[0] not in " \t":
                refuse(f"a multi-line string has text at column 0 on line {j + 1}")
            last = j
            j += 1
            continue
        if text[0] in " \t":
            if not here.comment_only:
                last = j
            j += 1
            continue
        break
    if last is None:
        refuse(f"'{name}' has no indented body")
    if last + 1 != end:
        refuse(f"Ghost says '{name}' ends at line {end}, but the text shows it ending at line {last + 1}")
    if not info[last].clean_end:
        refuse(f"'{name}' ends with an open bracket, string or backslash")

    # Decorators directly above belong to the block.
    first, k = d, d - 1
    while k >= 0 and not info[k].blank:
        ls = info[k].start
        if lines[ls].startswith("@") and not info[ls].cont:
            first, k = ls, ls - 1
        else:
            break
    k = first - 1
    while k >= 0 and (info[k].blank or info[k].comment_only):
        k -= 1
    if k >= 0 and lines[info[k].start].startswith("@"):
        refuse("a decorator above the definition is separated from it by blank or comment lines")

    _no_surprises(lines, info, first, last, name)
    _nothing_else_by_that_name(lines, info, first, last, name)
    return first, last


def _no_surprises(lines: Sequence[str], info: Sequence[_Line], first: int, last: int, name: str) -> None:
    tabs = spaces = False
    for i in range(first, last + 1):
        text = lines[i]
        if info[i].bad:
            refuse(f"line {i + 1}: a quote that never closes")
        if text.rstrip().endswith("\\"):
            refuse(f"line {i + 1}: a backslash line continuation")
        if "\x0c" in text or "\x0b" in text:
            refuse(f"line {i + 1}: a form-feed or vertical-tab character")
        if info[i].blank or info[i].cont:
            continue
        lead = text[:len(text) - len(text.lstrip(" \t"))]
        if "\t" in lead and " " in lead:
            refuse(f"line {i + 1}: tabs and spaces mixed in the indentation")
        tabs, spaces = tabs or "\t" in lead, spaces or " " in lead
    if tabs and spaces:
        refuse(f"'{name}' mixes tab-indented and space-indented lines")


def _nothing_else_by_that_name(lines: Sequence[str], info: Sequence[_Line], first: int, last: int,
                               name: str) -> None:
    again = re.compile(rf"(?:async def |def |class ){re.escape(name)}(?![A-Za-z0-9_])")
    decorated = re.compile(rf"^\s*@\s*{re.escape(name)}(?![A-Za-z0-9_])")
    for i, text in enumerate(lines):
        if first <= i <= last:
            continue
        if info[i].cont and info[i].in_string:
            continue          # prose inside a docstring is not code
        if again.match(text):
            refuse(f"'{name}' is defined again on line {i + 1}")
        if decorated.match(text):
            refuse(f"'{name}' is used as a decorator on line {i + 1}")
