"""The Drafter proposes. It imports only the shared data shapes and counts nothing itself.

The rule is an allowlist: a module of this package may import the standard library, this package, and the
named Warden and CNS modules below. Any other import fails, so a new dependency is a deliberate edit here.
"""

import ast
import sys
from pathlib import Path

import drafter

PACKAGE = Path(drafter.__file__).parent
README = (PACKAGE.parent / "README.md").read_text(encoding="utf-8")

#: Third-party modules the seat and fixers may import: the shared rows and Warden's proposal shapes.
ALLOWED_EVERYWHERE = {"warden.models", "cns.defect", "cns.seat"}
#: Modules only one file may import. The command line reads Ghost's JSON through Warden's own reader.
ALLOWED_ONLY_IN = {"warden.ghost": {"cli.py"}}
#: Never imported by anything here, whatever else is allowed: measuring or running things is not a maker's job.
_FORBIDDEN = {"burnish", "ghost_buster", "swizzle", "assay", "judge", "ast", "subprocess", "importlib"}


def _imports(path: Path) -> set[str]:
    """Every module the file imports, by its full dotted name. Relative imports are this package's own."""
    found: set[str] = set()
    for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
        if isinstance(node, ast.Import):
            found.update(a.name for a in node.names)
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            found.add(node.module)
    return found


def _outside_the_standard_library(module: str) -> bool:
    top = module.split(".")[0]
    return top not in sys.stdlib_module_names and top != "drafter" and top != "__future__"


def _third_party() -> dict[str, set[str]]:
    """Module name -> the files (relative to the package) that import it."""
    used: dict[str, set[str]] = {}
    for p in PACKAGE.rglob("*.py"):
        for module in _imports(p):
            if _outside_the_standard_library(module):
                used.setdefault(module, set()).add(p.relative_to(PACKAGE).as_posix())
    return used


def test_no_module_imports_another_role_or_measures_the_tree():
    offenders = {str(p.relative_to(PACKAGE)): sorted({m.split(".")[0] for m in _imports(p)} & _FORBIDDEN)
                 for p in PACKAGE.rglob("*.py") if {m.split(".")[0] for m in _imports(p)} & _FORBIDDEN}
    assert offenders == {}


def test_every_import_is_standard_library_this_package_or_on_the_allowlist():
    unexpected = {}
    for module, files in _third_party().items():
        if module in ALLOWED_EVERYWHERE:
            continue
        only = ALLOWED_ONLY_IN.get(module)
        stray = sorted(f.rsplit("/", 1)[-1] for f in files) if only is None else sorted(
            f for f in files if f.rsplit("/", 1)[-1] not in only)
        if only is None or stray:
            unexpected[module] = stray
    assert unexpected == {}, f"imports outside the allowlist: {unexpected}"


def test_the_allowlist_is_tight_so_the_docs_cannot_overstate_it():
    """Everything allowed is actually used, and the README names each of them."""
    used = set(_third_party())
    assert used == ALLOWED_EVERYWHERE | set(ALLOWED_ONLY_IN), (
        f"allowlist and imports disagree: unused {sorted((ALLOWED_EVERYWHERE | set(ALLOWED_ONLY_IN)) - used)}, "
        f"unlisted {sorted(used - ALLOWED_EVERYWHERE - set(ALLOWED_ONLY_IN))}")
    for module in sorted(used):
        assert f"`{module}`" in README, f"README does not mention the import of {module}"


def test_the_drafter_never_opens_a_file_for_writing():
    source = "\n".join(p.read_text(encoding="utf-8") for p in PACKAGE.rglob("*.py"))
    assert ".write_text(" not in source and "open(" not in source and ".write_bytes(" not in source
