"""The dead_code fixer checks, by plain text, that Ghost's span is exactly one definition.

The red team's cases: a span that overshoots into the next function, a span that
stops mid-body, and a decorator stranded above a removed def. Each is a refusal
with a recorded reason, never a damaged file.
"""

import pytest

from support import BOM, dead_finding, propose


def _write(tmp_path, text, newline=None):
    root = tmp_path / "tgt"
    root.mkdir(parents=True)
    (root / "m.py").write_bytes(text.encode("utf-8") if newline is None else text.replace("\n", newline).encode("utf-8"))
    return root


def _old(tmp_path, text, **kw):
    proposal, drafter = propose(_write(tmp_path, text), dead_finding(**kw))
    return (proposal.edits[0].old if proposal else None), drafter


KEEP = "def keep():\n    return 1\n\n\n"


def test_the_plain_case_removes_exactly_the_definition(tmp_path):
    old, _ = _old(tmp_path, KEEP + "def orphan():\n    return 2\n", start=5, end=6)
    assert old == "def orphan():\n    return 2\n"


def test_a_span_that_overshoots_into_the_next_function_is_refused(tmp_path):
    text = KEEP + "def orphan():\n    return 2\n\n\ndef in_use():\n    return 3\n"
    old, drafter = _old(tmp_path, text, start=5, end=10)
    assert old is None and "the text shows it ending at line 6" in drafter.last_skipped[0][1]


def test_a_span_that_stops_mid_body_is_refused(tmp_path):
    text = KEEP + "def orphan():\n    x = 1\n    return x\n"
    old, drafter = _old(tmp_path, text, start=5, end=6)
    assert old is None and "the text shows it ending at line 7" in drafter.last_skipped[0][1]


def test_a_decorator_directly_above_goes_with_the_def(tmp_path):
    text = KEEP + "@decorator\ndef orphan():\n    return 2\n"
    old, _ = _old(tmp_path, text, start=6, end=7)          # Ghost starts at the def, not the decorator
    assert old == "@decorator\ndef orphan():\n    return 2\n"


def test_several_and_multi_line_decorators_all_go(tmp_path):
    text = KEEP + "@one\n@two(\n    1,\n)\ndef orphan():\n    return 2\n"
    old, _ = _old(tmp_path, text, start=9, end=10)
    assert old == "@one\n@two(\n    1,\n)\ndef orphan():\n    return 2\n"


def test_a_decorator_separated_by_a_comment_is_refused_not_stranded(tmp_path):
    text = KEEP + "@decorator\n# note\ndef orphan():\n    return 2\n"
    old, drafter = _old(tmp_path, text, start=7, end=8)
    assert old is None and "decorator" in drafter.last_skipped[0][1]


def test_a_class_and_an_async_def_are_handled(tmp_path):
    old, _ = _old(tmp_path, KEEP + "class Orphan:\n    x = 1\n", name="Orphan", kind="class", start=5, end=6)
    assert old == "class Orphan:\n    x = 1\n"
    old, _ = _old(tmp_path / "b", KEEP + "async def orphan():\n    return 2\n", start=5, end=6)
    assert old == "async def orphan():\n    return 2\n"


def test_a_signature_over_several_lines_with_the_closer_at_column_zero(tmp_path):
    text = KEEP + "def orphan(\n    a,\n    b,\n):\n    return a + b\n"
    old, _ = _old(tmp_path, text, start=5, end=9)
    assert old == "def orphan(\n    a,\n    b,\n):\n    return a + b\n"


def test_blank_lines_and_a_docstring_inside_the_body_are_part_of_it(tmp_path):
    text = KEEP + 'def orphan():\n    """Doc."""\n\n    x = 1\n\n    return x\n\n\ndef keep2():\n    return 4\n'
    old, _ = _old(tmp_path, text, start=5, end=10)
    assert old == 'def orphan():\n    """Doc."""\n\n    x = 1\n\n    return x\n'


def test_a_trailing_comment_after_the_last_statement_does_not_change_the_end(tmp_path):
    text = KEEP + "def orphan():\n    return 2\n    # trailing note\n\n\nX = 1\n"
    old, _ = _old(tmp_path, text, start=5, end=6)
    assert old == "def orphan():\n    return 2\n"


def test_a_definition_at_the_end_of_the_file_without_a_final_newline(tmp_path):
    old, _ = _old(tmp_path, KEEP + "def orphan():\n    return 2", start=5, end=6)
    assert old == "def orphan():\n    return 2"


@pytest.mark.parametrize("text, why", [
    (KEEP + "def orphan(): return 2\n", "body on the header line"),
    (KEEP + "class Orphan: pass\n", "body on the header line"),
])
def test_a_one_line_definition_is_refused(tmp_path, text, why):
    name, kind = ("Orphan", "class") if "class" in text else ("orphan", "function")
    old, drafter = _old(tmp_path, text, name=name, kind=kind, start=5, end=5)
    assert old is None and why in drafter.last_skipped[0][1]


def test_tabs_mixed_with_spaces_are_refused(tmp_path):
    text = KEEP + "def orphan():\n\tx = 1\n    return x\n"
    old, drafter = _old(tmp_path, text, start=5, end=7)
    assert old is None and "tab" in drafter.last_skipped[0][1]


def test_a_backslash_continuation_is_refused(tmp_path):
    text = KEEP + "def orphan():\n    return 1 + \\\n        2\n"
    old, drafter = _old(tmp_path, text, start=5, end=7)
    assert old is None and "backslash" in drafter.last_skipped[0][1]


def test_a_multi_line_string_with_text_at_column_zero_is_refused(tmp_path):
    text = KEEP + 'def orphan():\n    return """\nflush left\n"""\n'
    old, drafter = _old(tmp_path, text, start=5, end=8)
    assert old is None and "column 0" in drafter.last_skipped[0][1]


def test_a_second_definition_of_the_same_name_is_refused(tmp_path):
    text = KEEP + "def orphan():\n    return 2\n\n\ndef orphan():\n    return 3\n"
    old, drafter = _old(tmp_path, text, start=5, end=6)
    assert old is None and "defined again" in drafter.last_skipped[0][1]


def test_the_name_used_as_a_decorator_elsewhere_is_refused(tmp_path):
    text = KEEP + "def orphan():\n    return 2\n\n\n@orphan\ndef other():\n    return 3\n"
    old, drafter = _old(tmp_path, text, start=5, end=6)
    assert old is None and "decorator" in drafter.last_skipped[0][1]


def test_a_definition_that_only_looks_like_one_inside_a_docstring_is_refused(tmp_path):
    text = 'DOC = """\ndef orphan():\n    return 2\n"""\n'
    old, drafter = _old(tmp_path, text, start=2, end=3)
    assert old is None and drafter.last_skipped


def test_a_line_range_outside_the_file_is_refused(tmp_path):
    old, drafter = _old(tmp_path, KEEP + "def orphan():\n    return 2\n", start=5, end=99)
    assert old is None and "outside the file" in drafter.last_skipped[0][1]


def test_a_framework_hook_is_refused_with_a_reason(tmp_path):
    old, drafter = _old(tmp_path, KEEP + "def orphan():\n    return 2\n", start=5, end=6, hook="yes")
    assert old is None and "framework" in drafter.last_skipped[0][1]


def test_a_leading_bom_and_crlf_endings_are_preserved(tmp_path):
    text = BOM + KEEP + "def orphan():\n    return 2\n"
    root = _write(tmp_path, text, newline="\r\n")
    proposal, _ = propose(root, dead_finding(start=5, end=6))
    assert proposal.edits[0].old == "def orphan():\r\n    return 2\r\n"
    first = BOM + "def orphan():\n    return 2\n"
    root2 = _write(tmp_path / "b", first, newline="\r\n")
    proposal, _ = propose(root2, dead_finding(start=1, end=2))
    assert proposal.edits[0].old == "def orphan():\r\n    return 2\r\n"          # the BOM is left out of the edit


def test_the_same_input_gives_the_same_proposal(tmp_path):
    root = _write(tmp_path, KEEP + "@d\ndef orphan():\n    return 2\n")
    finding = dead_finding(start=6, end=7)
    first, _ = propose(root, finding)
    second, _ = propose(root, finding)
    assert [(e.path, e.kind, e.old, e.new) for e in first.edits] == [(e.path, e.kind, e.old, e.new) for e in second.edits]
