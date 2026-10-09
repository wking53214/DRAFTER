"""The doc fixer replaces only the claim phrase, and refuses where a rewrite could do harm."""

import re

import pytest

from support import BOM, doc_finding, propose

NEW = "at least 79 `test_*` functions (an earlier version of this document gave 16)"
NEW_START = "The suite holds " + NEW


def _readme(tmp_path, text, name="README.md", newline=None):
    root = tmp_path / "tgt"
    root.mkdir(exist_ok=True)
    data = text if newline is None else text.replace("\n", newline)
    (root / name).write_bytes(data.encode("utf-8"))
    return root


def _run(tmp_path, text, line, name="README.md", **kw):
    root = _readme(tmp_path, text, name)
    return propose(root, doc_finding(file=name, line=line, **kw))


def _new(tmp_path, text, line, **kw):
    proposal, drafter = _run(tmp_path, text, line, **kw)
    return (proposal.edits[0].new if proposal else None), drafter


@pytest.mark.parametrize("line, expected", [
    ("Coverage is 95%, 16 tests passed, 3 bugs fixed.", f"Coverage is 95%, {NEW}, 3 bugs fixed."),
    ("**Tests:** 16 tests passed.", f"**Tests:** {NEW}."),
    ("**16 tests passed** on CI.", f"**{NEW}** on CI."),
    ("Dr. Smith says 10 tests passed.".replace("10", "16"), f"Dr. Smith says {NEW}."),
    ("We ran all 16 tests.", f"We ran {NEW}."),
    ("The suite has 16 tests, all passing.", f"The suite has {NEW}, all passing."),
    ("Status (16 tests passed) is green.", f"Status ({NEW}) is green."),
    ("All 16 tests passed on CI.", f"{NEW_START} on CI."),
    ("- 16 tests passed.", f"- {NEW_START}."),
    ("1. 16 tests passed.", f"1. {NEW_START}."),
    ("> 16 tests passed.", f"> {NEW_START}."),
    ("Done. Then 16 tests passed.", f"Done. Then {NEW}."),
])
def test_only_the_claim_phrase_changes(tmp_path, line, expected):
    text = f"# T\n\n{line}\n\nOther text.\n"
    new, _ = _new(tmp_path, text, 3)
    assert new == f"# T\n\n{expected}\n\nOther text.\n"
    assert not re.search(r"\b16\s+tests?\b", new)


def test_the_other_facts_in_the_sentence_survive(tmp_path):
    new, _ = _new(tmp_path, "# T\n\nCoverage is 95%, 16 tests passed, 3 bugs fixed.\n", 3)
    assert "Coverage is 95%" in new and "3 bugs fixed" in new


def test_only_the_first_of_two_identical_claims_on_a_line_is_replaced(tmp_path):
    new, _ = _new(tmp_path, "# T\n\nThe suite: 16 tests passed; again 16 tests passed.\n", 3)
    assert new.count("an earlier version") == 1 and "again 16 tests passed" in new


@pytest.mark.parametrize("line, why", [
    ("See [16 tests passed](https://ci.example/run) for details.", "square brackets"),
    ("![16 tests passed](https://img.example/b.svg)", "square brackets"),
    ("[![ci](https://img.example/b.svg)](https://ci.example/16 tests passed)", "link target"),
    ("[ci]: https://ci.example/16 tests passed", "square brackets|URL"),
    ("<https://ci.example/16 tests passed>", "HTML tag"),
    ("Run `16 tests passed` to see.", "backticks"),
    ("Run ``a ` 16 tests passed`` to see.", "backticks"),
    ("A stray ` tick then 16 tests passed.", "backticks"),
    ("Python 3.10 tests passed on CI.", "part of something else"),
    ("Release v2-16 tests passed.", "part of something else"),
    ("Path /x/16 tests passed.", "part of something else"),
    ("Use a/16 tests passed.", "part of something else"),
    ("Total 1,16 tests passed.", "part of something else"),
])
def test_a_claim_in_the_wrong_place_is_refused_with_a_reason(tmp_path, line, why):
    new, drafter = _new(tmp_path, f"# T\n\n{line.replace('Python 3.10', 'Python 3.16')}\n", 3)
    assert new is None
    assert re.search(why, drafter.last_skipped[0][1]), drafter.last_skipped


def test_python_3_10_tests_passed_is_refused_not_mangled(tmp_path):
    new, drafter = _new(tmp_path, "# T\n\nPython 3.10 tests passed on CI.\n", 3, documented=10)
    assert new is None and "part of something else" in drafter.last_skipped[0][1]


def test_dr_smith_is_not_cut_at_the_full_stop(tmp_path):
    new, _ = _new(tmp_path, "# T\n\nDr. Smith says 10 tests passed.\n", 3, documented=10)
    assert new == "# T\n\nDr. Smith says at least 79 `test_*` functions (an earlier version of this document gave 10).\n"


@pytest.mark.parametrize("text, line, why", [
    ("```\nThe suite: 16 tests passed.\n```\n", 2, "fenced"),
    ("~~~text\nThe suite: 16 tests passed.\n~~~\n", 2, "fenced"),
    ("````\n```\n16 tests passed.\n```\n````\n", 3, "fenced"),
    ("```\nnever closed\n16 tests passed.\n", 3, "fenced"),
    ("Text\n\n    16 tests passed.\n", 3, "indented"),
    ("Text\n\n\t16 tests passed.\n", 3, "indented"),
    ("# 16 tests passed\n", 1, "heading"),
    ("### The suite: 16 tests passed ###\n", 1, "heading"),
    ("The suite: 16 tests passed\n===\n", 1, "setext"),
    ("The suite: 16 tests passed\n---\n", 1, "setext"),
    ("Two line\nheading with 16 tests passed\n-----\n", 2, "setext"),
    ("| suite | 16 tests passed |\n|---|---|\n", 1, "table"),
    ("suite | 16 tests passed\n", 1, "table"),
    ("<!--\n16 tests passed.\n-->\n", 2, "HTML comment"),
    ("<!-- 16 tests passed. -->\n", 1, "HTML comment"),
    ("<p>16 tests passed.</p>\n", 1, "HTML tag"),
    ("---\ntitle: x\nnote: 16 tests passed\n---\n", 3, "front matter"),
])
def test_structure_that_a_rewrite_would_damage_is_refused(tmp_path, text, line, why):
    new, drafter = _new(tmp_path, text, line)
    assert new is None
    assert why in drafter.last_skipped[0][1], drafter.last_skipped


def test_a_claim_after_a_closed_fence_is_fine(tmp_path):
    new, _ = _new(tmp_path, "```\ncode\n```\n\nThe suite: 16 tests passed.\n", 5)
    assert new == f"```\ncode\n```\n\nThe suite: {NEW}.\n"


@pytest.mark.parametrize("name", ["CHANGELOG.md", "changelog.md", "HISTORY.md", "NEWS.md", "RELEASES.md",
                                  "CHANGELOG-2026.md", "History.md"])
def test_changelog_style_files_are_refused(tmp_path, name):
    proposal, drafter = _run(tmp_path, "# T\n\nThe suite: 16 tests passed.\n", 3, name=name)
    assert proposal is None and "changelog" in drafter.last_skipped[0][1]


def test_fullwidth_digits_are_refused(tmp_path):
    new, drafter = _new(tmp_path, "# T\n\nThe suite: １６ tests passed.\n", 3)
    assert new is None and "no '16 tests' claim" in drafter.last_skipped[0][1]


def test_a_leading_zero_number_is_refused(tmp_path):
    new, drafter = _new(tmp_path, "# T\n\nThe suite: 016 tests passed.\n", 3)
    assert new is None and drafter.last_skipped


def test_a_claim_split_over_two_lines_is_refused(tmp_path):
    new, drafter = _new(tmp_path, "# T\n\nThe suite: 16\ntests passed.\n", 3)
    assert new is None and drafter.last_skipped


@pytest.mark.parametrize("lower, documented", [(16, 16), (10, 16), (0, 16), (-5, 16)])
def test_a_new_number_that_is_not_higher_is_refused(tmp_path, lower, documented):
    new, drafter = _new(tmp_path, "# T\n\nThe suite: 16 tests passed.\n", 3, lower=lower, documented=documented)
    assert new is None and drafter.last_skipped


@pytest.mark.parametrize("bad", ["abc", "", None, "7.5", "７９", True, 3.5])
def test_a_bad_number_in_the_finding_is_refused(tmp_path, bad):
    root = _readme(tmp_path, "# T\n\nThe suite: 16 tests passed.\n")
    finding = doc_finding()
    finding["attributes"]["static_lower_bound"] = bad
    proposal, drafter = propose(root, finding)
    assert proposal is None and drafter.last_skipped


def test_a_bad_line_number_is_refused(tmp_path):
    for line in (0, 99, -1, "3", None, True, 2.5):
        root = _readme(tmp_path, "# T\n\nThe suite: 16 tests passed.\n")
        finding = doc_finding()
        finding["evidence"]["line_start"] = line
        proposal, drafter = propose(root, finding)
        assert proposal is None and drafter.last_skipped, line


def test_the_edit_touches_only_the_claim_bytes_with_a_bom_and_crlf(tmp_path):
    text = BOM + "# T\n\nCoverage 95%: 16 tests passed, 3 bugs fixed.\n\nEnd\n"
    root = _readme(tmp_path, text, newline="\r\n")
    proposal, _ = propose(root, doc_finding(line=3))
    (edit,) = proposal.edits
    assert edit.old.startswith(BOM + "# T\n") and edit.new.startswith(BOM + "# T\n")      # Warden shows CRLF files with LF
    assert edit.new == edit.old.replace("16 tests passed", NEW)


def test_mixed_line_endings_are_kept_exactly(tmp_path):
    root = tmp_path / "tgt"
    root.mkdir()
    raw = "# T\r\n\nThe suite: 16 tests passed.\r\nEnd\n"
    (root / "README.md").write_bytes(raw.encode("utf-8"))
    proposal, _ = propose(root, doc_finding(line=3))
    (edit,) = proposal.edits
    assert edit.new == raw.replace("16 tests passed", NEW)


def test_a_lone_carriage_return_counts_as_a_line_break_like_ghost_does(tmp_path):
    root = tmp_path / "tgt"
    root.mkdir()
    (root / "README.md").write_bytes(b"# T\rThe suite: 16 tests passed.\r")
    proposal, _ = propose(root, doc_finding(line=2))
    assert proposal.edits[0].new == f"# T\rThe suite: {NEW}.\r"


def test_the_same_input_gives_the_same_proposal(tmp_path):
    root = _readme(tmp_path, "# T\n\nThe suite: 16 tests passed.\n")
    a, _ = propose(root, doc_finding(line=3))
    b, _ = propose(root, doc_finding(line=3))
    assert [(e.path, e.kind, e.old, e.new) for e in a.edits] == [(e.path, e.kind, e.old, e.new) for e in b.edits]
