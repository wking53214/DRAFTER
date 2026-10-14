"""Ghost's `list_membership_in_loop`: `x in NAME` inside a loop, where NAME is a module-level list.

Each pass of the loop scans the whole list; a set makes the lookup constant-time.
The fix changes the literal's brackets and nothing else: `NAME = [a, b, c]`
becomes `NAME = {a, b, c}` (a tuple's parentheses the same way). Every other
character of the file stays as it was.

That is only safe when a set means the same thing as the list everywhere the
name is used. The Drafter proves that by reading tokens, not by guessing, and
refuses with a recorded reason whenever it cannot:

* the literal must sit at column 0 as `NAME = [...]` or `NAME = (...)`, assigned
  exactly once in the file, and every element must be a plain literal that is
  hashable and compares the same way in a set: a string (no f-string), a whole
  or decimal number with an optional minus, or `None`, `True`, `False`;
* in the same file, every other mention of NAME must be a membership test
  (`in NAME`, `not in NAME`). Iteration (`for x in NAME`) is refused, because a
  set has no order; indexing, slicing, `len`, concatenation, a method call, a
  rebinding, an attribute, an export: all refused;
* NAME must appear nowhere else in the repository (another module, a string, a
  stub, a config or docs file), which is the same rule the dead-code fixer uses.

Tokens come from the standard library's tokenizer. It builds no syntax tree and
decides nothing about the program; it only says where strings, names and
brackets begin and end, which is what a hand-rolled scanner gets wrong. A file
the tokenizer cannot read is refused.
"""

from __future__ import annotations

import io
import re
import tokenize
from pathlib import Path
from typing import Optional

from warden.models import Defect, FileEdit

from .._reach import _files
from .._safe import (Reason, attributes_of, check_editable, read_source, refuse,
                     resolve_in_target, run_fixer, split_lines, warden_view, whole_int)

_NUMBER = re.compile(r"[0-9]+(?:\.[0-9]+)?", re.ASCII)
#: String prefixes whose value is a plain str or bytes. An f-string is an expression, not a literal.
_STRING_PREFIX = re.compile(r"(?:[rbuRBU]|[rR][bB]|[bB][rR])?", re.ASCII)
_CONSTANTS = {"None", "True", "False"}
_OPEN = {"[": "]", "(": ")"}
#: Python 3.12+ gives f-strings their own token type; older versions tokenize them as STRING with an f prefix.
_FSTRING_START = getattr(tokenize, "FSTRING_START", -1)


def fix_list_membership(target: Path, defect: Defect, why: Optional[Reason] = None) -> Optional[FileEdit]:
    return run_fixer(lambda: _fix(target, defect), why)


def _fix(target: Path, defect: Defect) -> FileEdit:
    attrs = attributes_of(defect)
    name = attrs.get("name")
    if not isinstance(name, str) or not name.isidentifier() or not name.isascii():
        refuse("Ghost does not name the container (an older Ghost reports only the sentence); nothing to act on")
    container = attrs.get("container")
    if container not in ("list", "tuple"):
        refuse(f"Ghost says the container is {container!r}, not a list or tuple literal")
    defined_at = whole_int(attrs.get("defined_at"), "defined_at")
    path, rel = resolve_in_target(target, getattr(defect, "file", None))
    if path.suffix != ".py":
        refuse(f"{rel.as_posix()} is not a .py file")
    check_editable(rel)
    text = read_source(path)
    body = text[1:] if text.startswith("﻿") else text
    tokens = _tokens(body)
    first, last = _definition(tokens, name, container, defined_at)
    _only_membership_elsewhere(tokens, name, first, last)
    _nowhere_else(target, path, name)
    new_body = _rebracket(body, tokens[first], tokens[last])
    prefix = "﻿" if text.startswith("﻿") else ""
    return FileEdit(path=rel.as_posix(), kind="write", new=warden_view(prefix + new_body), old=warden_view(text))


# --- reading the file --------------------------------------------------------

def _tokens(body: str) -> list[tokenize.TokenInfo]:
    try:
        return list(tokenize.generate_tokens(io.StringIO(body).readline))
    except (tokenize.TokenError, SyntaxError, IndentationError) as err:
        refuse(f"the file could not be tokenized ({type(err).__name__}), so it is left alone")
    raise AssertionError  # unreachable


def _significant(tok: tokenize.TokenInfo) -> bool:
    return tok.type not in (tokenize.NL, tokenize.COMMENT, tokenize.ENCODING)


def _definition(tokens: list[tokenize.TokenInfo], name: str, container: str, defined_at: int) -> tuple[int, int]:
    """(index of the opening bracket, index of the closing bracket) of the one module-level literal."""
    found: list[tuple[int, int]] = []
    for i, tok in enumerate(tokens):
        if tok.type != tokenize.NAME or tok.string != name or tok.start[1] != 0:
            continue
        rest = [k for k in range(i + 1, len(tokens)) if _significant(tokens[k])]
        if len(rest) < 2 or tokens[rest[0]].string != "=" or tokens[rest[1]].string not in _OPEN:
            continue
        open_at = rest[1]
        close_at = _elements(tokens, open_at, name)
        after = next((k for k in range(close_at + 1, len(tokens)) if _significant(tokens[k])), None)
        if after is None or tokens[after].type not in (tokenize.NEWLINE, tokenize.ENDMARKER):
            refuse(f"the statement defining {name} does not end with the literal")
        found.append((open_at, close_at))
    if not found:
        refuse(f"no module-level `{name} = [...]` or `{name} = (...)` was found at column 0")
    if len(found) > 1:
        refuse(f"{name} is bound to a literal more than once in the file")
    open_at, close_at = found[0]
    opener = tokens[open_at].string
    if (opener == "[") != (container == "list"):
        refuse(f"Ghost says {name} is a {container}, but the literal opens with {opener!r}")
    if tokens[open_at].start[0] != defined_at and tokens[open_at - 2].start[0] != defined_at:
        refuse(f"Ghost says {name} is defined on line {defined_at}, but the literal found starts on "
               f"line {tokens[open_at].start[0]}")
    return open_at, close_at


def _elements(tokens: list[tokenize.TokenInfo], open_at: int, name: str) -> int:
    """Check every element of the literal and return the index of its closing bracket."""
    closer = _OPEN[tokens[open_at].string]
    k = open_at + 1
    count = 0
    expect_element = True
    while k < len(tokens):
        tok = tokens[k]
        if not _significant(tok):
            k += 1
            continue
        if tok.type == tokenize.OP and tok.string == closer:
            if count == 0:
                refuse(f"{name} is an empty literal")
            return k
        if tok.type == tokenize.OP and tok.string == ",":
            if expect_element:
                refuse(f"{name} has a stray comma on line {tok.start[0]}")
            expect_element = True
            k += 1
            continue
        if not expect_element:
            refuse(f"{name} has two elements with no comma between them on line {tok.start[0]}")
        k = _one_element(tokens, k, name)
        count += 1
        expect_element = False
    refuse(f"the literal defining {name} never closes")
    raise AssertionError  # unreachable


def _one_element(tokens: list[tokenize.TokenInfo], k: int, name: str) -> int:
    """Check one element starting at token k; return the index just past it."""
    tok = tokens[k]
    if tok.type == tokenize.OP and tok.string == "-":
        k += 1
        tok = tokens[k] if k < len(tokens) else tok
        if tok.type != tokenize.NUMBER:
            refuse(f"{name} has a minus sign before something that is not a number on line {tok.start[0]}")
    if tok.type == tokenize.NUMBER:
        if not _NUMBER.fullmatch(tok.string):
            refuse(f"{name} holds a number that is not a plain whole or decimal number ({tok.string!r}); "
                   "its value in a set might not compare the way the list did")
        return k + 1
    if tok.type == tokenize.STRING:
        prefix = re.match(r"[A-Za-z]*", tok.string).group(0)
        if not _STRING_PREFIX.fullmatch(prefix):
            refuse(f"{name} holds a string with the prefix {prefix!r} (an f-string is an expression, not a literal)")
        nxt = next((tokens[j] for j in range(k + 1, len(tokens)) if _significant(tokens[j])), None)
        if nxt is not None and nxt.type == tokenize.STRING:
            refuse(f"{name} has two string literals side by side on line {tok.start[0]} (implicit concatenation)")
        return k + 1
    if tok.type == tokenize.NAME and tok.string in _CONSTANTS:
        return k + 1
    if tok.type == _FSTRING_START:                 # Python 3.12+ tokenizes f-strings in pieces
        refuse(f"{name} holds an f-string on line {tok.start[0]}, which is an expression, not a literal")
    refuse(f"{name} holds an element that is not a plain literal on line {tok.start[0]} ({tok.string[:30]!r})")
    raise AssertionError  # unreachable


# --- every other use of the name -------------------------------------------

def _only_membership_elsewhere(tokens: list[tokenize.TokenInfo], name: str, open_at: int, close_at: int) -> None:
    """Refuse unless every other mention of `name` in the file is a membership test."""
    sig = [i for i, t in enumerate(tokens) if _significant(t)]
    pos = {idx: n for n, idx in enumerate(sig)}
    for i, tok in enumerate(tokens):
        if tok.type == tokenize.STRING and re.search(r"(?<![A-Za-z0-9_])%s(?![A-Za-z0-9_])" % re.escape(name), tok.string):
            refuse(f"{name} appears inside a string on line {tok.start[0]}, so it may be looked up by name")
        if tok.type != tokenize.NAME or tok.string != name:
            continue
        if i == open_at - 2:
            continue                               # the definition itself
        n = pos[i]
        before = tokens[sig[n - 1]] if n > 0 else None
        after = tokens[sig[n + 1]] if n + 1 < len(sig) else None
        if before is None or before.string != "in":
            refuse(f"{name} is used on line {tok.start[0]} in a way that is not a membership test "
                   f"({_shape(before, after)}); a set would not mean the same thing there")
        if after is not None and after.type == tokenize.OP and after.string in ("[", ".", "("):
            refuse(f"{name} is indexed, called or dereferenced on line {tok.start[0]}")
        if _is_iteration(tokens, sig, n):
            refuse(f"line {tok.start[0]} iterates over {name} (`for ... in {name}`), and a set has no order")


def _shape(before, after) -> str:
    left = before.string if before is not None else "start of file"
    right = after.string if after is not None else "end of file"
    return f"between {left!r} and {right!r}"


def _is_iteration(tokens: list[tokenize.TokenInfo], sig: list[int], n: int) -> bool:
    """True when the `in` before the name belongs to a `for`, not to a membership test.

    Walking back over the logical line to the nearest `for`: if no other `in` lies between
    that `for` and ours, ours is the loop's. `[y for y in xs if y in NAME]` has one in between
    (membership); `for x in NAME` and `[y for y in NAME]` have none (iteration).
    """
    k = n - 1                                      # the `in`
    seen_in = 0
    j = k - 1
    while j >= 0:
        tok = tokens[sig[j]]
        if tok.type in (tokenize.NEWLINE, tokenize.INDENT, tokenize.DEDENT):
            return False
        if tok.type == tokenize.NAME and tok.string == "for":
            return seen_in == 0
        if tok.type == tokenize.NAME and tok.string == "in":
            seen_in += 1
        j -= 1
    return False


def _nowhere_else(target: Path, own: Path, name: str) -> None:
    """Refuse if any other file in the repository mentions the name at all."""
    word = re.compile(r"(?<![A-Za-z0-9_])%s(?![A-Za-z0-9_])" % re.escape(name))
    root = Path(target).resolve()
    own = own.resolve()
    for path, text in _files(root):
        if path.resolve() == own:
            continue
        for number, line in enumerate(text.splitlines()):
            if word.search(line):
                refuse(f"{name} is mentioned in {path.relative_to(root).as_posix()}:{number + 1}, so another "
                       "file may use it as a list")


# --- the edit -----------------------------------------------------------------

def _rebracket(body: str, opener: tokenize.TokenInfo, closer: tokenize.TokenInfo) -> str:
    """The same text with the literal's two brackets replaced by braces."""
    rows = split_lines(body)
    lines = [c for c, _ in rows]

    def swap(tok: tokenize.TokenInfo, new: str) -> None:
        row, col = tok.start[0] - 1, tok.start[1]
        line = lines[row]
        if line[col:col + 1] != tok.string:
            refuse(f"the bracket on line {row + 1} is not where the tokenizer said it was")
        lines[row] = line[:col] + new + line[col + 1:]

    swap(opener, "{")
    swap(closer, "}")
    return "".join(c + e for c, (_, e) in zip(lines, rows))
