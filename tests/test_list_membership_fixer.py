"""The list-membership fixer turns one module-level list into a set, and only when that changes nothing."""

from pathlib import Path

import pytest

from warden.models import defects_from_ghost

from drafter import Drafter
from support import full_gate_kwargs, init_repo, real_findings

TEN = '"a", "b", "c", "d", "e", "f", "g", "h", "i", "j"'
SOURCE = f'''BLOCKED = [{TEN}]


def scan(items):
    hits = 0
    for item in items:
        if item in BLOCKED:
            hits += 1
    return hits
'''


def _finding(file="pkg/mod.py", name="BLOCKED", container="list", defined_at=1, line=7, extra=None):
    attrs = {"kind": "list_membership_in_loop", "name": name, "container": container,
             "defined_at": str(defined_at)}
    if extra is not None:
        attrs = extra
    return {"id": "ghost-list1", "severity": "minor", "status": "confirmed",
            "summary": f"mod.py:{line} `in {name}`, a module-level list inside a loop",
            "detector": "list_membership_in_loop", "attributes": attrs,
            "evidence": {"file": file, "line_start": line}}


def _repo(root: Path, source: str = SOURCE, others: dict | None = None) -> None:
    (root / "pkg").mkdir(exist_ok=True)
    (root / "pkg" / "__init__.py").write_text("", encoding="utf-8")
    (root / "pkg" / "mod.py").write_text(source, encoding="utf-8")
    (root / "tests").mkdir(exist_ok=True)
    (root / "tests" / "test_m.py").write_text(
        "from pkg.mod import scan\n\ndef test_scan():\n    assert scan(['a', 'z']) == 1\n", encoding="utf-8")
    (root / "pyproject.toml").write_text('[project]\nname = "d"\nversion = "0.0.1"\n'
                                         '[tool.pytest.ini_options]\npythonpath = ["."]\n', encoding="utf-8")
    for rel, text in (others or {}).items():
        p = root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text, encoding="utf-8")


def _propose(root: Path, **kw):
    drafter = Drafter()
    return drafter.propose(root, defects_from_ghost([_finding(**kw)]), "base"), drafter


def _reason(drafter: Drafter) -> str:
    return " | ".join(r for _, r in drafter.last_skipped)


def test_the_list_becomes_a_set_and_nothing_else_changes(tmp_path):
    _repo(tmp_path)
    proposal, _ = _propose(tmp_path)
    (edit,) = proposal.edits
    assert edit.path == "pkg/mod.py"
    assert edit.new == SOURCE.replace(f"[{TEN}]", f"{{{TEN}}}")
    assert proposal.transformation_scope == "code" and proposal.scope_hint == "code"


def test_a_tuple_literal_is_handled_the_same_way(tmp_path):
    _repo(tmp_path, SOURCE.replace(f"[{TEN}]", f"({TEN})"))
    proposal, _ = _propose(tmp_path, container="tuple")
    assert proposal.edits[0].new.startswith(f"BLOCKED = {{{TEN}}}\n")


def test_a_multi_line_literal_with_comments_keeps_every_other_byte(tmp_path):
    source = ('BLOCKED = [\n    "a", "b",  # first\n    "c", "d", "e",\n    "f", "g", "h", "i", "j",\n]\n\n'
              'def scan(items):\n    return [i for i in items if i in BLOCKED]\n')
    _repo(tmp_path, source)
    proposal, _ = _propose(tmp_path, line=8)
    expected = source.replace("BLOCKED = [", "BLOCKED = {").replace('"j",\n]', '"j",\n}')
    assert proposal.edits[0].new == expected


def test_crlf_and_bom_are_kept(tmp_path):
    source = "﻿" + SOURCE.replace("\n", "\r\n")
    _repo(tmp_path, source)
    proposal, _ = _propose(tmp_path)
    (edit,) = proposal.edits
    assert edit.new.startswith("﻿BLOCKED = {") and "\r\n" not in edit.new   # Warden's view of a CRLF file
    assert edit.old.startswith("﻿BLOCKED = [")


def test_numbers_none_and_negatives_are_fine(tmp_path):
    source = SOURCE.replace(f"[{TEN}]", "[1, 2, 3, 4, 5, 6, 7, 8, 9, -10, 2.5, None, True]")
    _repo(tmp_path, source)
    proposal, _ = _propose(tmp_path)
    assert "BLOCKED = {1, 2, 3, 4, 5, 6, 7, 8, 9, -10, 2.5, None, True}" in proposal.edits[0].new


@pytest.mark.parametrize("literal, why", [
    (f'[{TEN}, f"{{x}}"]', "f-string"),
    (f'[{TEN}, "k" "l"]', "side by side"),
    (f'[{TEN}, (1, 2)]', "not a plain literal"),
    (f'[{TEN}, some_name]', "not a plain literal"),
    (f'[{TEN}, 0x1F]', "not a plain whole or decimal number"),
    ('[]', "empty"),
    (f'[{TEN},, "k"]', "stray comma"),
])
def test_an_element_that_is_not_a_plain_literal_is_refused(tmp_path, literal, why):
    _repo(tmp_path, SOURCE.replace(f"[{TEN}]", literal))
    proposal, drafter = _propose(tmp_path)
    assert proposal is None and why in _reason(drafter)


@pytest.mark.parametrize("use, why", [
    ("    for b in BLOCKED:\n        pass\n", "iterates"),
    ("    return [b for b in BLOCKED]\n", "iterates"),
    ("    return BLOCKED[0]\n", "not a membership test"),
    ("    return len(BLOCKED)\n", "not a membership test"),
    ("    return BLOCKED + items\n", "not a membership test"),
    ("    BLOCKED.append(items)\n", "not a membership test"),
    ("    return sorted(BLOCKED)\n", "not a membership test"),
    ("    return BLOCKED\n", "not a membership test"),
    ("    return getattr(items, 'BLOCKED')\n", "inside a string"),
    ("    return f(BLOCKED=1)\n", "not a membership test"),
])
def test_any_other_use_in_the_file_is_refused(tmp_path, use, why):
    _repo(tmp_path, SOURCE + "\n\ndef other(items):\n" + use)
    proposal, drafter = _propose(tmp_path)
    assert proposal is None and why in _reason(drafter), _reason(drafter)


def test_a_membership_test_inside_a_comprehension_is_still_a_membership_test(tmp_path):
    _repo(tmp_path, SOURCE + "\n\ndef other(items):\n    return [i for i in items if i in BLOCKED]\n"
                             "\n\ndef third(items):\n    return [i for i in items if i not in BLOCKED]\n")
    proposal, drafter = _propose(tmp_path)
    assert proposal is not None, _reason(drafter)


def test_a_second_binding_is_refused(tmp_path):
    _repo(tmp_path, SOURCE + '\nBLOCKED = ["z"]\n')
    proposal, drafter = _propose(tmp_path)
    assert proposal is None and "more than once" in _reason(drafter)


def test_a_mention_in_another_file_is_refused(tmp_path):
    _repo(tmp_path, others={"pkg/use.py": "from pkg.mod import BLOCKED\n\nfirst = BLOCKED[0]\n"})
    proposal, drafter = _propose(tmp_path)
    assert proposal is None and "pkg/use.py:1" in _reason(drafter)


def test_a_mention_in_docs_is_refused(tmp_path):
    _repo(tmp_path, others={"README.md": "BLOCKED is the list of names we refuse.\n"})
    proposal, drafter = _propose(tmp_path)
    assert proposal is None and "README.md:1" in _reason(drafter)


def test_ghosts_facts_must_match_the_file(tmp_path):
    _repo(tmp_path)
    assert _propose(tmp_path, container="tuple")[0] is None
    assert _propose(tmp_path, defined_at=3)[0] is None
    assert _propose(tmp_path, name="OTHER")[0] is None


def test_an_old_ghost_without_the_name_attribute_gets_no_proposal(tmp_path):
    _repo(tmp_path)
    proposal, drafter = _propose(tmp_path, extra={"kind": "list_membership_in_loop"})
    assert proposal is None and "does not name the container" in _reason(drafter)


def test_a_file_that_will_not_tokenize_is_left_alone(tmp_path):
    _repo(tmp_path, SOURCE + '\ns = "never closed\n')
    proposal, drafter = _propose(tmp_path)
    assert proposal is None and "tokenized" in _reason(drafter)


def test_test_files_are_never_edited(tmp_path):
    _repo(tmp_path)
    (tmp_path / "tests" / "test_data.py").write_text(SOURCE, encoding="utf-8")
    assert _propose(tmp_path, file="tests/test_data.py")[0] is None


def test_under_a_documentation_grant_it_is_skipped_with_a_reason(tmp_path):
    _repo(tmp_path)
    drafter = Drafter(scope="documentation")
    assert drafter.propose(tmp_path, defects_from_ghost([_finding()]), "base") is None
    assert "needs code scope" in _reason(drafter)


# --- with the real Ghost and the real Warden ---------------------------------

def test_the_real_ghost_finding_carries_what_the_fixer_needs(tmp_path):
    _repo(tmp_path)
    found = [f for f in real_findings(tmp_path) if f["detector"] == "list_membership_in_loop"]
    assert len(found) == 1
    attrs = found[0]["attributes"]
    assert attrs["name"] == "BLOCKED" and attrs["container"] == "list" and attrs["defined_at"] == "1"
    proposal = Drafter().propose(tmp_path, defects_from_ghost(found), "base")
    assert proposal is not None and "BLOCKED = {" in proposal.edits[0].new


def test_through_the_whole_gate_the_set_stands_and_ghost_is_silent(tmp_path):
    from warden.authorization import grant
    from warden.tagteam import TagTeam
    _repo(tmp_path)
    init_repo(tmp_path)
    auth = grant("william", "transform", str(tmp_path.resolve()), "code", "test")
    result = TagTeam(drafter=Drafter(), **full_gate_kwargs()).run(tmp_path, authorization=auth)
    assert result.decision == "ACCEPT", result.reason
    assert (tmp_path / "pkg" / "mod.py").read_text(encoding="utf-8").startswith("BLOCKED = {")
    assert [c.outcome for c in result.cycles] == ["APPLIED", "NOTHING_TO_PROPOSE"]
