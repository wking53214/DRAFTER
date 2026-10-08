"""The Proposer proposes. It imports only Elegant's data shapes and counts nothing itself."""

import ast
from pathlib import Path

import proposer

_FORBIDDEN = {"streamline", "ghost_buster", "swizzle", "touchstone", "ast", "subprocess"}


def _imports(path: Path) -> set[str]:
    names: set[str] = set()
    for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
        if isinstance(node, ast.Import):
            names.update(a.name.split(".")[0] for a in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
            names.add(node.module.split(".")[0])
    return names


def test_no_module_imports_another_role_or_measures_the_tree():
    root = Path(proposer.__file__).parent
    offenders = {str(p.relative_to(root)): sorted(_imports(p) & _FORBIDDEN)
                 for p in root.rglob("*.py") if _imports(p) & _FORBIDDEN}
    assert offenders == {}


def test_only_elegant_models_are_imported_from_elegant():
    root = Path(proposer.__file__).parent
    for p in root.rglob("*.py"):
        for node in ast.walk(ast.parse(p.read_text(encoding="utf-8"))):
            if isinstance(node, ast.ImportFrom) and node.module and node.module.split(".")[0] == "elegant":
                assert node.module == "elegant.models", (p.name, node.module)


def test_the_proposer_never_opens_a_file_for_writing():
    root = Path(proposer.__file__).parent
    source = "\n".join(p.read_text(encoding="utf-8") for p in root.rglob("*.py"))
    assert ".write_text(" not in source and "open(" not in source
