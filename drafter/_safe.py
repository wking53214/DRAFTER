"""Small, careful helpers shared by the fixers.

The Drafter's promise is "safe or silent": whatever it is handed, it either
proposes a change it can justify or proposes nothing and says why. Every helper
here either returns a clean value or raises `Refuse` with a plain-language
reason, and the fixers turn a `Refuse` into "no proposal, reason recorded".

Nothing here writes. Reading goes through `read_source`, which reads bytes and
decodes strictly, so a file that is not valid UTF-8 is a refusal, not a crash.
"""

from __future__ import annotations

import re
from pathlib import Path, PurePath
from typing import Any, Callable, Mapping, Optional

#: Reads nothing larger than this. A source or document bigger than 5 MB is not
#: something to rewrite by hand-rolled text scanning.
MAX_BYTES = 5_000_000

#: Folders the Drafter never proposes to touch (Warden also blocks them).
BLOCKED_DIRS = frozenset({
    "tests", ".git", ".venv", "venv", ".github", ".tox", ".nox", "node_modules",
    "site-packages", "__pycache__",
})
#: Files that configure or drive the test run. Never edited by a maker.
BLOCKED_FILES = frozenset({
    "conftest.py", "pyproject.toml", "pytest.ini", "tox.ini", "setup.cfg", "noxfile.py",
    ".coveragerc", "makefile",
})

Reason = Callable[[str], None]


class Refuse(Exception):
    """The Drafter will not propose a change, and this is why."""


def refuse(reason: str) -> None:
    raise Refuse(reason)


def whole_int(value: Any, what: str) -> int:
    """A whole number written with ASCII digits (as text or int). Anything else is refused."""
    if isinstance(value, bool):
        refuse(f"{what} is not a number")
    if isinstance(value, int):
        return value
    if isinstance(value, str) and re.fullmatch(r"[0-9]{1,9}", value):
        return int(value)
    refuse(f"{what} is not a whole number written with ASCII digits ({_shown(value)})")
    raise AssertionError  # unreachable; keeps type checkers calm


def attributes_of(defect: Any) -> Mapping[str, Any]:
    attrs = getattr(defect, "attributes", None)
    if not isinstance(attrs, Mapping):
        refuse("the finding carries no attributes mapping")
    return attrs


def finding_id(defect: Any) -> str:
    try:
        return str(getattr(defect, "identity", "") or "?")[:120]
    except Exception:  # noqa: BLE001 - an odd object must not stop the loop
        return "?"


def _shown(value: Any) -> str:
    text = repr(value)
    return text if len(text) <= 40 else text[:37] + "..."


def check_editable(rel: PurePath) -> None:
    """Refuse a path the Drafter must never propose to change."""
    parts = [p.lower() for p in rel.parts]
    for part in parts[:-1]:
        if part in BLOCKED_DIRS:
            refuse(f"{rel.as_posix()} is under '{part}', which the Drafter never edits")
    name = parts[-1]
    if (name in BLOCKED_FILES or (name.startswith("test_") and name.endswith(".py"))
            or name.endswith("_test.py")):
        refuse(f"{rel.as_posix()} is a test or test-configuration file, which the Drafter never edits")


def resolve_in_target(target: Path, file: Any) -> tuple[Path, PurePath]:
    """The finding's file as (absolute path, path relative to the target).

    The path is tried as given under the target first. Only if no such file
    exists is a leading folder equal to the target's own name stripped, because
    older Ghost output spelled a root-level file as `<target folder>/m.py`.
    The result must be a real file inside the target, reached without `..` and
    without passing through a symlink.
    """
    if not isinstance(file, str) or not file.strip():
        refuse("the finding names no file")
    if "\x00" in file:
        refuse("the finding's file path contains a NUL character")
    try:
        root = Path(target).resolve()
        given = Path(file)
        if ".." in given.parts:
            refuse(f"{file!r} climbs out of the folder with '..'")
        if given.is_absolute():
            try:
                given = given.relative_to(root)
            except ValueError:
                refuse(f"{file!r} is outside the target")
        if not given.parts:
            refuse("the finding's file path is empty")
        tries = [given]
        if len(given.parts) > 1 and given.parts[0] == root.name:
            tries.append(Path(*given.parts[1:]))
        for rel in tries:
            full = root / rel
            if _symlink_on_the_way(root, rel):
                refuse(f"{rel.as_posix()} passes through a symlink")
            if full.is_file():
                if not full.resolve().is_relative_to(root):
                    refuse(f"{rel.as_posix()} resolves outside the target")
                return full, rel
        refuse(f"no file {given.as_posix()!r} under the target"
               + (f" (also tried {tries[1].as_posix()!r})" if len(tries) > 1 else ""))
    except Refuse:
        raise
    except (OSError, ValueError) as err:
        refuse(f"the path could not be used ({type(err).__name__})")
    raise AssertionError  # unreachable


def _symlink_on_the_way(root: Path, rel: Path) -> bool:
    here = root
    for part in rel.parts:
        here = here / part
        if here.is_symlink():
            return True
    return False


def read_source(path: Path) -> str:
    """The file's text exactly as written (a leading BOM and CRLF are kept)."""
    try:
        if path.stat().st_size > MAX_BYTES:
            refuse(f"{path.name} is larger than {MAX_BYTES} bytes")
        raw = path.read_bytes()
    except OSError as err:
        refuse(f"{path.name} could not be read ({type(err).__name__})")
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError:
        refuse(f"{path.name} is not valid UTF-8, so it is left alone")
    if "\x00" in text:
        refuse(f"{path.name} contains a NUL character")
    return text


_LINE_END = re.compile(r"\r\n|\r|\n")


def split_lines(text: str) -> list[tuple[str, str]]:
    """(content, ending) for every line, split the way Python's universal newlines do.

    That is the way Ghost counted, so a line number from Ghost lands on the same line here.
    """
    out: list[tuple[str, str]] = []
    pos = 0
    for m in _LINE_END.finditer(text):
        out.append((text[pos:m.start()], m.group(0)))
        pos = m.end()
    if pos < len(text):
        out.append((text[pos:], ""))
    return out


def warden_view(text: str) -> str:
    """The text as Warden shows it to an edit: a file that is CRLF throughout reads with LF."""
    crlf = "\r\n" in text and text.count("\r\n") == text.count("\n") and "\r" not in text.replace("\r\n", "")
    return text.replace("\r\n", "\n") if crlf else text


def run_fixer(inner: Callable[[], Any], why: Optional[Reason]) -> Any:
    """Run a fixer body. A refusal (or any surprise) becomes None plus a recorded reason."""
    try:
        return inner()
    except Refuse as err:
        reason = str(err)
    except Exception as err:  # noqa: BLE001 - safe or silent: odd input must never crash the loop
        reason = f"unexpected {type(err).__name__} while checking the finding; left alone"
    if why is not None:
        why(reason)
    return None
