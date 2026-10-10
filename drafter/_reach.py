"""Could anything still reach this name? A conservative, text-only answer.

Ghost's `dead_code` says no syntax node refers to a name. That is not the same
as "nothing uses it": a string, a stub file, an `__all__` list, a config file,
a re-export, a computed lookup or a registering decorator all reach a name
without naming it in code. This module refuses (with a plain reason) whenever
any of those could be true. It reads text only; it never imports `ast`, never
runs anything and never writes.

The rule is "when in doubt, leave it". Any whole-word mention of the name
anywhere in the repository outside the definition itself is enough to refuse.
A caller wrapped in `try/except` is not evidence of safety, so it is not used.
"""

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Iterator, Sequence

from ._safe import refuse

_SKIP_DIRS = frozenset({".git", ".hg", ".svn", ".venv", "venv", "node_modules", "__pycache__",
                        ".tox", ".nox", "site-packages", ".mypy_cache", ".pytest_cache", ".ruff_cache"})
_MAX_FILE = 2_000_000
_MAX_FILES = 20_000

#: Decorators that cannot register anything. Every other decorator is treated as registering.
_PLAIN_DECORATORS = frozenset({"dataclass", "final", "cache", "lru_cache", "total_ordering"})
_CLASS_ROLE = re.compile(
    r"\b(?:Protocol|ABC|ABCMeta|metaclass|abstractmethod|abstractproperty|property|overload"
    r"|__init_subclass__|__set_name__|__subclasshook__|__class_getitem__)\b")
_DYNAMIC = re.compile(
    r"\b(?:globals|locals|vars|eval|exec|import_module|__import__)\s*\(|__dict__|sys\.modules\b|importlib")
_GETATTR = re.compile(r"\bgetattr\s*\(")
_STATIC_NAME = re.compile(r"""\s*(?:[rb]|rb|br)?(["'])[^"'\\]*\1\s*[,)]""", re.IGNORECASE)


def check_decorators(lines: Sequence[str], first: int, last: int, name: str, kind: str) -> None:
    """Refuse a block whose decorators could register it, or whose role is structural."""
    for k in range(first, last + 1):
        text = lines[k]
        if not text.startswith("@"):
            continue
        expr = text[1:].strip()
        if re.fullmatch(r"[A-Za-z_]\w*", expr) and expr in _PLAIN_DECORATORS:
            continue
        refuse(f"it has the decorator @{expr[:40]}, and a decorator with a call or attribute form "
               "(or any other) may register it with a framework")
    if name.startswith("__") and name.endswith("__"):
        refuse(f"{name} is a dunder name; Python itself may call it")
    if kind == "class":
        header = next((lines[k] for k in range(first, last + 1) if lines[k].startswith("class ")), "")
        if _CLASS_ROLE.search(header):
            refuse("the class declares a protocol, abstract or metaclass role")
        for k in range(first + 1, last + 1):
            if _CLASS_ROLE.search(lines[k]):
                refuse("the class body has an abstract, property, overload or class-hook role")
        bases = re.match(r"class\s+\w+\s*\((.*)\)\s*:", header.strip())
        if bases:
            for base in (b.strip() for b in bases.group(1).split(",") if b.strip()):
                if not (base == "object" or re.fullmatch(r"\w*(?:Error|Exception)", base)):
                    refuse(f"the class derives from {base[:40]}, whose machinery could register or use subclasses")


def _files(root: Path) -> Iterator[tuple[Path, str]]:
    seen = 0
    for here, dirs, names in os.walk(root, followlinks=False):
        dirs[:] = sorted(d for d in dirs if d not in _SKIP_DIRS)
        for n in sorted(names):
            p = Path(here, n)
            if p.is_symlink():
                continue
            seen += 1
            if seen > _MAX_FILES:
                refuse("the repository has too many files to check every mention of the name")
            try:
                if p.stat().st_size > _MAX_FILE:
                    refuse(f"{p.name} is too large to check for mentions of the name")
                raw = p.read_bytes()
            except OSError:
                refuse(f"{p.name} could not be read to check for mentions of the name")
            if b"\x00" in raw:
                continue
            yield p, raw.decode("utf-8", errors="replace")


def _why_mention(rel: str, line: str, name: str) -> str:
    stripped = line.strip()
    if rel.endswith(".pyi"):
        return "it is listed in a .pyi stub"
    if "__all__" in line:
        return "it is listed in an __all__"
    if re.search(r"\bimport\b", line) and re.search(r"\bfrom\b|\bimport\b", line):
        return "it is imported or re-exported by another line"
    if "TYPE_CHECKING" in line:
        return "it is used under TYPE_CHECKING"
    if re.search(r"""["'][^"']*\b%s\b[^"']*["']""" % re.escape(name), line):
        return "it appears inside a string (a lookup, a string annotation or a doc sample)"
    if re.search(r"\.%s\b" % re.escape(name), line):
        return "it is used as an attribute name"
    if rel.endswith((".yml", ".yaml", ".toml", ".json", ".cfg", ".ini")):
        return "it appears in a configuration file"
    if rel.endswith((".md", ".rst", ".txt")):
        return "it appears in documentation"
    if stripped.startswith("#"):
        return "it is mentioned in a comment"
    return "the name appears elsewhere in the repository"


def _dynamic_in(text: str) -> bool:
    if _DYNAMIC.search(text):
        return True
    for m in _GETATTR.finditer(text):
        depth, i, n = 1, m.end(), len(text)
        while i < n and depth:
            c = text[i]
            depth += (c in "([{") - (c in ")]}")
            if depth == 1 and c == ",":
                break
            i += 1
        if i >= n or not _STATIC_NAME.match(text, i + 1):
            return True
    return False


def check_unreachable(root: Path, rel: Path, name: str, own_first: int, own_last: int) -> None:
    """Refuse if anything in the repository could reach `name` other than its own definition."""
    word = re.compile(r"(?<![A-Za-z0-9_])%s(?![A-Za-z0-9_])" % re.escape(name))
    own = (root / rel).resolve()
    here_dir = own.parent
    stem = rel.stem
    star = re.compile(r"from\s+[\w.]*\b%s\s+import\s+\*" % re.escape(stem)) if stem != "__init__" else None
    markers = _lookup_markers(name)
    for path, text in _files(root):
        relp = path.relative_to(root).as_posix()
        is_own = path.resolve() == own
        for number, line in enumerate(text.splitlines()):
            if is_own and own_first <= number <= own_last:
                continue
            if word.search(line):
                refuse(f"{_why_mention(relp, line, name)} ({relp}:{number + 1}); "
                       "a name mentioned anywhere is treated as possibly in use")
        if star and path.suffix == ".py" and star.search(text):
            refuse(f"{relp} star-imports this module, so the name may be re-exported")
        if path.suffix == ".py":
            if path.resolve().parent == here_dir and _dynamic_in(text):
                refuse(f"{relp} looks things up by a computed name (getattr, globals, importlib or similar) "
                       "in the same package, so a static scan cannot prove the name unused")
            for marker in markers:
                if marker.search(text):
                    refuse(f"{relp} builds names from a piece of this one ({marker.pattern[:30]}...), "
                           "so it may be looked up dynamically")


def _lookup_markers(name: str) -> list[re.Pattern[str]]:
    """Quoted fragments such as 'cmd_' or '_handler' that a computed lookup would glue the rest onto."""
    out: list[re.Pattern[str]] = []
    cuts = [i + 1 for i, c in enumerate(name) if c == "_" and 0 < i + 1 < len(name)]
    for i in cuts:
        pre, post = name[:i], name[i - 1:]
        if len(pre.strip("_")) >= 2:
            out.append(re.compile(r"""["']%s(?:["']|\{|%%)""" % re.escape(pre)))
        if len(post.strip("_")) >= 2:
            out.append(re.compile(r"""(?:["']|\})%s["']""" % re.escape(post)))
    return out
