"""Safe or silent: odd input gives no proposal and a recorded reason, never a crash."""

import pytest
from warden.models import Defect, DefectSeverity

from drafter import Drafter
from support import dead_finding, doc_finding, propose

SRC = "def used():\n    return 1\n\n\ndef orphan():\n    return 2\n"


def _root(tmp_path, **files):
    root = tmp_path / "tgt"
    root.mkdir()
    for name, data in files.items():
        (root / name).write_bytes(data if isinstance(data, bytes) else data.encode("utf-8"))
    return root


def test_a_python_file_that_is_not_utf8_is_left_alone(tmp_path):
    root = _root(tmp_path, **{"m.py": b"# caf\xe9\n" + SRC.encode()})
    proposal, drafter = propose(root, dead_finding(start=6, end=7))
    assert proposal is None and "not valid UTF-8" in drafter.last_skipped[0][1]


def test_a_markdown_file_that_is_not_utf8_is_left_alone(tmp_path):
    root = _root(tmp_path, **{"README.md": b"# T\n\nThe suite: 16 tests passed \xff\n"})
    proposal, drafter = propose(root, doc_finding())
    assert proposal is None and "not valid UTF-8" in drafter.last_skipped[0][1]


def test_a_file_with_a_nul_byte_is_left_alone(tmp_path):
    root = _root(tmp_path, **{"m.py": SRC.encode() + b"\x00"})
    proposal, drafter = propose(root, dead_finding())
    assert proposal is None and "NUL" in drafter.last_skipped[0][1]


def test_a_folder_where_a_file_should_be_is_left_alone(tmp_path):
    root = _root(tmp_path)
    (root / "m.py").mkdir()
    proposal, drafter = propose(root, dead_finding())
    assert proposal is None and drafter.last_skipped


def _defect(**kw):
    base = dict(summary="s", severity=DefectSeverity.LOW, ghost_id="ghost-x", detector="dead_code",
                file="m.py", line=1, attributes={})
    base.update(kw)
    return Defect(**base)


@pytest.mark.parametrize("change", [
    {"attributes": None}, {"attributes": "text"}, {"attributes": ["a"]}, {"attributes": {}},
    {"file": None}, {"file": ""}, {"file": 5}, {"file": "a\x00b.py"}, {"file": "   "},
    {"line": "x"}, {"line": None}, {"line": -3}, {"line": 2.5},
    {"detector": None}, {"detector": 7}, {"detector": ["dead_code"]},
])
@pytest.mark.parametrize("detector", ["dead_code", "doc_test_count_drift"])
def test_defects_with_odd_fields_never_crash(tmp_path, change, detector):
    root = _root(tmp_path, **{"m.py": SRC, "README.md": "# T\n\nThe suite: 16 tests passed.\n"})
    drafter = Drafter()
    attrs = (dead_finding()["attributes"] if detector == "dead_code" else doc_finding()["attributes"])
    kw = {"detector": detector, "attributes": attrs, "file": "m.py" if detector == "dead_code" else "README.md",
          "line": 3}
    kw.update(change)
    proposal = drafter.propose(root, (_defect(**kw),), "base")
    if "line" in change and detector == "dead_code":
        return          # the dead_code fixer takes its lines from Ghost's attributes, so line is not used
    assert proposal is None


@pytest.mark.parametrize("key, value", [
    ("name", None), ("name", 5), ("name", "not an identifier"), ("name", "a.b"), ("kind", None), ("kind", "method"),
    ("line_start", "x"), ("line_start", None), ("line_start", "5.5"), ("line_start", "-1"), ("line_start", True),
    ("line_end", "x"), ("line_end", ""), ("framework_hook", None), ("framework_hook", "maybe"),
])
def test_dead_code_attributes_of_the_wrong_type_are_refused(tmp_path, key, value):
    root = _root(tmp_path, **{"m.py": SRC})
    finding = dead_finding()
    finding["attributes"][key] = value
    proposal, drafter = propose(root, finding)
    assert proposal is None and drafter.last_skipped


@pytest.mark.parametrize("junk", [None, "text", 5, 3.5, [], ["x"], ("a",), object(), b"bytes"])
def test_items_that_are_not_findings_are_ignored(tmp_path, junk):
    root = _root(tmp_path, **{"m.py": SRC})
    drafter = Drafter()
    assert drafter.propose(root, (junk,), "base") is None
    assert drafter.last_skipped


def test_a_good_finding_after_junk_is_still_proposed(tmp_path):
    root = _root(tmp_path, **{"m.py": SRC})
    from warden.models import defects_from_ghost
    items = (None, "junk", *defects_from_ghost([dead_finding(start=5, end=6)]))
    proposal = Drafter().propose(root, items, "base")
    assert proposal is not None and len(Drafter().propose(root, items, "base").edits) == 1


def test_raw_mapping_findings_are_accepted_and_broken_ones_are_not(tmp_path):
    root = _root(tmp_path, **{"m.py": SRC})
    drafter = Drafter()
    assert drafter.propose(root, (dead_finding(),), "base") is not None
    broken = dead_finding()
    broken["evidence"] = "not a mapping"
    assert drafter.propose(root, (broken,), "base") is None and drafter.last_skipped


@pytest.mark.parametrize("observed", [None, 5, object(), ()])
def test_a_findings_argument_that_is_not_a_list_gives_nothing(tmp_path, observed):
    root = _root(tmp_path, **{"m.py": SRC})
    assert Drafter().propose(root, observed, "base") is None


@pytest.mark.parametrize("target", [None, 5, "no/such/folder\x00", "/definitely/not/here"])
def test_a_bad_target_gives_nothing(target):
    drafter = Drafter()
    assert drafter.propose(target, (), "base") is None


def test_a_fixer_that_blows_up_is_contained_and_reported(tmp_path):
    root = _root(tmp_path, **{"m.py": SRC})

    def broken(target, defect):
        raise RuntimeError("boom")

    drafter = Drafter({"dead_code": broken})
    from warden.models import defects_from_ghost
    assert drafter.propose(root, defects_from_ghost([dead_finding()]), "base") is None
    assert "RuntimeError" in drafter.last_skipped[0][1]


def test_findings_of_other_kinds_are_not_listed_as_skipped(tmp_path):
    root = _root(tmp_path, **{"m.py": SRC})
    other = dead_finding()
    other["detector"] = "long_function"
    proposal, drafter = propose(root, other)
    assert proposal is None and drafter.last_skipped == []


def test_the_skip_list_is_per_call_and_readable(tmp_path):
    root = _root(tmp_path, **{"m.py": SRC})
    drafter = Drafter()
    from warden.models import defects_from_ghost
    drafter.propose(root, defects_from_ghost([dead_finding(file="gone.py")]), "base")
    assert drafter.describe_skipped()[0].startswith("skipped ghost-dead1: no file")
    drafter.propose(root, defects_from_ghost([dead_finding(start=5, end=6)]), "base")
    assert drafter.last_skipped == []


def test_the_first_finding_it_cannot_use_does_not_hide_the_next(tmp_path):
    root = _root(tmp_path, **{"m.py": SRC})
    from warden.models import defects_from_ghost
    bad = dead_finding(file="gone.py", fid="ghost-bad")
    good = dead_finding(fid="ghost-good")
    drafter = Drafter()
    proposal = drafter.propose(root, defects_from_ghost([bad, good]), "base")
    assert proposal.known_defects[0].ghost_id == "ghost-good"
    assert drafter.last_skipped[0][0] == "ghost-bad"
