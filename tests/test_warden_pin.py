"""Warden is pinned to a tag or commit, never to a moving branch."""

import re
import tomllib
from pathlib import Path

PYPROJECT = Path(__file__).resolve().parent.parent / "pyproject.toml"
WARDEN = re.compile(r"^warden @ git\+https://github\.com/wking53214/Warden\.git@(?P<ref>[^\s@]+)$")
PINNED = re.compile(r"^(?:[0-9a-f]{40}|v\d+\.\d+\.\d+)$")


def _warden_dependency() -> re.Match:
    deps = tomllib.loads(PYPROJECT.read_text(encoding="utf-8"))["project"]["dependencies"]
    found = [m for d in deps if (m := WARDEN.match(d))]
    assert len(found) == 1, f"expected exactly one pinned Warden dependency, got {deps}"
    return found[0]


def test_warden_is_pinned_to_a_tag_or_a_full_commit():
    ref = _warden_dependency().group("ref")
    assert PINNED.match(ref), f"Warden is pinned to {ref!r}; use a vX.Y.Z tag or a full 40-character commit"


def _pin_comment() -> str:
    line = next(ln for ln in PYPROJECT.read_text(encoding="utf-8").splitlines() if ln.lstrip().startswith('"warden @ '))
    return line.split("#", 1)[1] if "#" in line else ""


def test_the_pin_comment_names_the_installed_warden_release():
    """The comment beside the pin says which Warden release the commit is. It must agree with what got installed."""
    from importlib import metadata

    installed = metadata.version("warden")
    assert f"Warden {installed}" in _pin_comment(), f"pin comment {_pin_comment()!r} vs installed {installed}"


def test_the_cns_pin_text_equals_wardens_own_cns_requirement():
    """Warden requires CNS by its release tag. pip treats a tag URL and a commit URL as two sources, so this
    package's pin text must equal Warden's requirement text exactly."""
    from importlib import metadata

    drafter_deps = tomllib.loads(PYPROJECT.read_text(encoding="utf-8"))["project"]["dependencies"]
    (mine,) = [d for d in drafter_deps if d.startswith("cns @ ")]
    theirs = [r.split(";")[0].strip() for r in (metadata.requires("warden") or []) if r.startswith("cns @ ")]
    assert theirs == [mine.split("#")[0].strip()], f"Warden requires {theirs}, Drafter pins {mine}"
