"""The Drafter proposes. It imports only the shared data shapes and counts nothing itself.

The rule is an allowlist: a module of this package may import the standard library, this package, and the
named Warden and CNS modules below. Any other import fails, so a new dependency is a deliberate edit here.
"""

import ast
import re
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


#: The one place the package opens anything for writing: the null device, so a failed delivery cannot raise again
#: when the interpreter flushes stdout at exit. It writes nothing anywhere. Each entry is (file, enclosing function).
WRITE_ALLOWLIST = {("cli.py", "_silence_stdout")}
#: Calls that can open a file, by dotted name. For these the mode argument decides.
_OPENERS = {"io.open", "io.FileIO", "codecs.open", "gzip.open", "bz2.open", "lzma.open", "tarfile.open"}
#: Calls that change the filesystem whatever their arguments.
_ALWAYS_WRITES = {"os.open", "os.remove", "os.unlink", "os.rename", "os.replace", "os.mkdir", "os.makedirs",
                  "os.rmdir", "os.removedirs", "os.truncate", "os.ftruncate", "os.symlink", "os.link", "os.chmod",
                  "os.write", "os.fdopen", "os.mkfifo", "os.utime", "os.chown", "builtins.exec", "builtins.eval",
                  "builtins.__import__"}
_ALWAYS_WRITES_PREFIXES = ("shutil.", "tempfile.", "fileinput.")
#: Methods that write or change files on a path object or a file object, whatever the receiver is called.
_WRITE_METHODS = {"write_text", "write_bytes", "touch", "mkdir", "unlink", "rmdir", "rename", "symlink_to",
                  "hardlink_to", "chmod", "truncate", "write", "writelines"}


def _aliases(tree: ast.AST) -> dict[str, str]:
    """Local name -> the dotted name it stands for, for plain imports and `from x import y as z`."""
    names: dict[str, str] = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for a in node.names:
                names[(a.asname or a.name).split(".")[0]] = a.name if a.asname else a.name.split(".")[0]
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            for a in node.names:
                names[a.asname or a.name] = f"{node.module}.{a.name}"
    return names


def _dotted(node: ast.AST, names: dict[str, str]) -> str:
    if isinstance(node, ast.Name):
        builtin = "builtins." + node.id if node.id in {"open", "exec", "eval", "__import__"} else node.id
        return names.get(node.id, builtin)
    if isinstance(node, ast.Attribute):
        base = _dotted(node.value, names)
        return f"{base}.{node.attr}" if base else node.attr
    return ""


def _can_write(call: ast.Call, method: bool) -> bool:
    """Does this opener call open for writing, or is its mode not a plain read mode we can see?

    `method` is the `something.open(...)` form (a path object): the mode is the first argument and is only believed
    when it looks like a mode string. Otherwise the mode is the second argument, as in `open(name, mode)`.
    """
    mode: ast.AST | None = None
    for kw in call.keywords:
        if kw.arg == "mode":
            mode = kw.value
        elif kw.arg is None:
            return True                                             # **kwargs: the mode cannot be seen
    if mode is None:
        if method:
            first = call.args[0] if call.args else None
            if first is None:
                return False                                        # Path.open() with no arguments reads
            mode = first
        elif len(call.args) > 1:
            mode = call.args[1]
        else:
            return False                                            # open(name) reads
    if isinstance(mode, ast.Constant) and isinstance(mode.value, str):
        if method and not re.fullmatch(r"[rwxabt+]{1,3}", mode.value):
            return True                                             # not a mode string: cannot tell what it is
        return any(c in mode.value for c in "wax+")
    return True                                      # a computed mode cannot be shown to be a read


def write_sites(source: str) -> list[tuple[str, int]]:
    """(enclosing function, line) of every call in `source` that opens or changes a file, or runs computed code."""
    tree = ast.parse(source)
    names = _aliases(tree)
    found: list[tuple[str, int]] = []

    def visit(node: ast.AST, scope: str) -> None:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            scope = node.name
        if isinstance(node, ast.Call):
            dotted = _dotted(node.func, names)
            attr = node.func.attr if isinstance(node.func, ast.Attribute) else ""
            function_form = dotted in _OPENERS or dotted == "builtins.open"
            method_form = attr == "open" and not function_form
            if (dotted in _ALWAYS_WRITES or dotted.startswith(_ALWAYS_WRITES_PREFIXES) or attr in _WRITE_METHODS
                    or ((function_form or method_form) and _can_write(node, method_form))):
                found.append((scope, node.lineno))
        for child in ast.iter_child_nodes(node):
            visit(child, scope)

    visit(tree, "<module>")
    return found


def test_the_write_checker_sees_every_spelling_it_is_meant_to():
    """The guard is only worth something if it fails on the spellings a substring search misses."""
    spellings = [
        "open('f', 'w')", "open('f', mode='a')", "open('f', 'r+')", "open('f', mode)", "open('f', **kw)",
        "import io\nio.FileIO('f', 'wb')", "from io import FileIO as F\nF('f', 'wb')", "import io\nio.open('f', 'x')",
        "import os\nos.open('f', os.O_WRONLY)", "import os\nos.devnull and os.replace('a', 'b')",
        "from pathlib import Path\nPath('f').write_text('x')", "Path('f').write_bytes(b'x')",
        "Path('f').open('w')", "Path('f').touch()", "import shutil\nshutil.copy('a', 'b')",
        "import tempfile\ntempfile.mkstemp()", "import os\nos.fdopen(1, 'w')", "f.write('x')", "eval('1')",
    ]
    for source in spellings:
        assert write_sites(source), f"the checker misses: {source!r}"
    reads = ["open('f')", "open('f', 'r')", "open('f', 'rb')", "Path('f').read_text()", "Path('f').read_bytes()",
             "'a'.replace('a', 'b')", "import os\nos.path.join('a', 'b')", "Path('f').open()"]
    for source in reads:
        assert write_sites(source) == [], f"the checker flags a plain read: {source!r}"


def test_the_drafter_never_opens_a_file_for_writing():
    """No call in the package opens a file for writing or changes the filesystem, except the one named null-device site.

    This replaces a substring search that `io.FileIO(...)`, `Path.write_text`-by-another-name, `os.open` and an
    aliased import all slipped past. The allowlist is exact: if the allowed site goes away the test says so, so the
    list cannot outlive the code.
    """
    found = {(p.relative_to(PACKAGE).as_posix(), scope)
             for p in PACKAGE.rglob("*.py") for scope, _ in write_sites(p.read_text(encoding="utf-8"))}
    assert found == WRITE_ALLOWLIST, (f"unexpected: {sorted(found - WRITE_ALLOWLIST)}; "
                                      f"gone: {sorted(WRITE_ALLOWLIST - found)}")
    cli = (PACKAGE / "cli.py").read_text(encoding="utf-8")
    assert 'io.FileIO(os.devnull, "wb")' in cli, "the allowed site must open the null device and nothing else"
