"""Ghost's `doc_test_count_drift`: a document claims N tests and the suite has grown past it.

Every number comes from Ghost's finding (the claim, the lower bound on the real
count, the line, and whether Ghost judged the claim safe to edit). The Drafter
counts nothing itself.

The edit is as small as it can be: only the claim phrase (the number, the word
"tests" and a following "passed", "passing" or "collected") is replaced. The
rest of the line, and of the file, is left byte for byte as it was, including a
leading BOM and the line endings. A claim that sits in a place where rewriting
could do harm is refused with a recorded reason: inside a link, image, URL,
backticks or HTML tag, in a code block, heading or table row, in a changelog,
or when the number looks like part of something else (a version such as 3.10).
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Optional

from warden.models import Defect, FileEdit

from .._safe import (Reason, attributes_of, check_editable, read_source, refuse,
                     resolve_in_target, run_fixer, split_lines, warden_view, whole_int)

#: The number, "test(s)", and an optional "passed/passing/collected". ASCII digits only.
_CLAIM = re.compile(
    r"(?P<all>\ball\s+)?(?<![0-9])(?P<num>[0-9]+)\s+tests?\b(?P<verb>\s+(?:passing|passed|collected)\b)?",
    re.IGNORECASE | re.ASCII)
#: What may sit directly in front of the claim. Anything else (3.10, v2-16, a/16) is "part of something else".
_PRECEDING_OK = set(" \t*(\"':;")
_MARKER = re.compile(r"^(?:[ ]{0,3}(?:(?:[-*+]|>|\d{1,9}[.)])[ \t]+)*)")
_ATX = re.compile(r"^ {0,3}#{1,6}(?:[ \t]|$)")
_UNDERLINE = re.compile(r"^ {0,3}(?:=+|-+)[ \t]*$")
_FENCE = re.compile(r"^ {0,3}(`{3,}|~{3,})(.*)$")
_HISTORY = ("CHANGELOG", "HISTORY", "NEWS", "RELEASES")


def fix_doc_test_count(target: Path, defect: Defect, why: Optional[Reason] = None) -> Optional[FileEdit]:
    return run_fixer(lambda: _fix(target, defect), why)


def _fix(target: Path, defect: Defect) -> FileEdit:
    attrs = attributes_of(defect)
    if attrs.get("writable") != "yes":
        refuse(f"Ghost does not mark the claim writable ({attrs.get('not_writable_because') or 'no reason given'})")
    documented = whole_int(attrs.get("documented_count"), "documented_count")
    lower = whole_int(attrs.get("static_lower_bound"), "static_lower_bound")
    line_no = getattr(defect, "line", None)
    if line_no is None or isinstance(line_no, bool) or not isinstance(line_no, int) or line_no < 1:
        refuse("the finding gives no usable line number")
    if lower < 1:
        refuse("the lower bound is not a positive number")
    if lower <= documented:
        refuse(f"the claim ({documented}) is not below Ghost's lower bound ({lower}), so it is not an undercount")
    path, rel = resolve_in_target(target, getattr(defect, "file", None))
    if path.suffix.lower() != ".md":
        refuse(f"{rel.as_posix()} is not a Markdown file")
    check_editable(rel)
    if path.name.upper().startswith(_HISTORY):
        refuse(f"{path.name} is a changelog-style record of the past, not a live claim")
    text = read_source(path)
    body = text[1:] if text.startswith("\ufeff") else text
    rows = split_lines(body)
    if line_no > len(rows):
        refuse(f"line {line_no} is past the end of the file ({len(rows)} lines)")
    contents = [r[0] for r in rows]
    _only_prose(contents, line_no - 1)
    line = contents[line_no - 1]
    new_line = _rewrite(line, documented, lower)
    new_rows = list(rows)
    new_rows[line_no - 1] = (new_line, rows[line_no - 1][1])
    prefix = "\ufeff" if text.startswith("\ufeff") else ""
    new = prefix + "".join(c + e for c, e in new_rows)
    return FileEdit(path=rel.as_posix(), kind="write", new=warden_view(new), old=warden_view(text))


# --- where the claim sits -------------------------------------------------

def _only_prose(lines: list[str], index: int) -> None:
    """Refuse if line `index` is not ordinary paragraph or list text.

    Fences, HTML comments and front matter are tracked from the top of the file,
    because whether a line is code depends on what came before it.
    """
    fence: Optional[tuple[str, int]] = None
    in_comment = False
    if lines and lines[0].strip() == "---":                 # front matter runs to the next ---
        end = next((k for k in range(1, len(lines)) if lines[k].strip() in {"---", "..."}), len(lines))
        if index <= end:
            refuse("the line is inside the file's front matter")
    for i, line in enumerate(lines[:index + 1]):
        m = _FENCE.match(line)
        if fence is not None:
            if m and m.group(1)[0] == fence[0] and len(m.group(1)) >= fence[1] and not m.group(2).strip():
                fence = None
            if i == index:
                refuse("the line is inside a fenced code block")
            continue
        if in_comment:
            in_comment = "-->" not in line
            if i == index:
                refuse("the line is inside an HTML comment")
            continue
        if m and not (m.group(1)[0] == "`" and "`" in m.group(2)):
            fence = (m.group(1)[0], len(m.group(1)))
            if i == index:
                refuse("the line is a code fence")
            continue
        if "<!--" in line:
            in_comment = "-->" not in line[line.find("<!--") + 4:]
            if i == index:
                refuse("the line holds an HTML comment")
    line = lines[index]
    if line.startswith("\t") or len(line) - len(line.lstrip(" ")) >= 4:
        refuse("the line is indented like a code block")
    if _ATX.match(line):
        refuse("the line is a heading")
    if line.lstrip().startswith("<"):
        refuse("the line starts with an HTML tag")
    if "|" in line:
        refuse("the line looks like a table row")
    if _UNDERLINE.match(line):
        refuse("the line is a heading underline or divider")
    k = index + 1
    while k < len(lines) and lines[k].strip():
        if _UNDERLINE.match(lines[k]) and not re.match(r"^\s*([-*+]|\d+[.)])\s", lines[index]):
            refuse("the line is the text of an underlined (setext) heading")
        k += 1


def _spans(line: str, opening: str, closing: str) -> list[tuple[int, int]]:
    """Matched (start, end) pairs of a bracket kind on one line; end is exclusive."""
    stack, found = [], []
    for i, c in enumerate(line):
        if c == opening:
            stack.append(i)
        elif c == closing and stack:
            found.append((stack.pop(), i + 1))
    return found


def _code_spans(line: str) -> list[tuple[int, int]]:
    spans, i, n = [], 0, len(line)
    while i < n:
        if line[i] != "`":
            i += 1
            continue
        j = i
        while j < n and line[j] == "`":
            j += 1
        run = line[i:j]
        close = line.find(run, j)
        while close != -1 and (close + len(run) < n and line[close + len(run)] == "`"):
            close = line.find(run, close + len(run) + 1)
        if close == -1:
            spans.append((i, n))            # an unclosed backtick: treat the rest as code
            return spans
        spans.append((i, close + len(run)))
        i = close + len(run)
    return spans


def _protected(line: str, s: int, e: int) -> Optional[str]:
    for a, b in _code_spans(line):
        if a < e and s < b:
            return "the claim is inside backticks"
    for a, b in _spans(line, "[", "]"):
        if a < e and s < b:
            return "the claim is inside square brackets (a link, image or badge)"
    if line[:s].count("[") > line[:s].count("]") or line[:s].count("]") > line[:s].count("["):
        return "the claim follows an unbalanced square bracket"
    for m in re.finditer(r"\]\(", line):
        close = _matching_paren(line, m.end() - 1)
        if m.start() < e and s < close:
            return "the claim is inside a link target"
    for a, b in _spans(line, "<", ">"):
        if a < e and s < b:
            return "the claim is inside an HTML tag or autolink"
    token_start = max(line.rfind(" ", 0, s), line.rfind("\t", 0, s)) + 1
    if "://" in line[token_start:s] or re.match(r"^\s*\[[^\]]*\]:", line):
        return "the claim is inside a URL or link definition"
    return None


def _matching_paren(line: str, open_at: int) -> int:
    depth = 0
    for i in range(open_at, len(line)):
        if line[i] == "(":
            depth += 1
        elif line[i] == ")":
            depth -= 1
            if depth == 0:
                return i + 1
    return len(line)


# --- the edit itself ------------------------------------------------------

def _rewrite(line: str, documented: int, lower: int) -> str:
    marker_end = len(_MARKER.match(line).group(0))
    first_problem: Optional[str] = None
    for m in _CLAIM.finditer(line):
        if m.group("num") != str(documented):
            continue
        if not m.group("verb") and not re.match(r"\s*[,.]", line[m.end():]):
            continue                      # not the shape Ghost reports (it needs passed/passing/collected or , .)
        s, e = m.start(), m.end()
        problem = _claim_problem(line, s, e)
        if problem:
            first_problem = first_problem or problem
            continue
        at_start = line[:s].strip() == "" or s == marker_end
        claim = (f"at least {lower} `test_*` functions "
                 f"(an earlier version of this document gave {documented})")
        if at_start:
            claim = "The suite holds " + claim
        return line[:s] + claim + line[e:]
    refuse(first_problem or f"no '{documented} tests' claim found on that line")
    raise AssertionError  # unreachable


def _claim_problem(line: str, s: int, e: int) -> Optional[str]:
    where = _protected(line, s, e)
    if where:
        return where
    before = line[s - 1] if s else " "
    if before not in _PRECEDING_OK:
        return "the number looks like part of something else (a version, path or longer figure)"
    if e < len(line) and (line[e].isalnum() or line[e] in "_-/"):
        return "the claim runs into the next word"
    return None
