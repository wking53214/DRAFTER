"""The README's evidence and its ledger point at things that exist, and the README keeps the sections it promises.

A claim of "works" in the README names a test, a CI job or a command. This file fails if a named test is gone, if the
ledger cites a version or a date the CHANGELOG does not have, if a number the README states has drifted from the file
that holds it, or if marketing words come back.
"""

import re
import tomllib
from pathlib import Path

import drafter

REPO = Path(drafter.__file__).resolve().parent.parent
README = (REPO / "README.md").read_text(encoding="utf-8")
CHANGELOG = (REPO / "CHANGELOG.md").read_text(encoding="utf-8")
WORKFLOW = (REPO / ".github" / "workflows" / "tests.yml").read_text(encoding="utf-8")
PYPROJECT_TEXT = (REPO / "pyproject.toml").read_text(encoding="utf-8")
TESTS = {path.name: path.read_text(encoding="utf-8") for path in (REPO / "tests").glob("test_*.py")}

REQUIRED_HEADINGS = (
    "## WHAT THIS IS",
    "## HOW TO INSTALL AND RUN",
    "## WHAT WORKS",
    "## WHAT DOES NOT WORK / NOT PROVEN",
    "## KNOWN DEFECTS",
    "## WHAT BROKE AND HOW IT WAS FIXED",
    "## SELF-HOSTING",
    "## CEILINGS CODE CANNOT FIX",
)
BANNED_WORDS = ("robust", "powerful", "production-ready", "production ready", "seamless", "comprehensive",
                "blazing", "enterprise", "battle-tested", "state-of-the-art")
TAG_STATE_PHRASES = ("not tagged", "untagged", "no tag", "no release tag", "once a release tag exists",
                     "tag exists", "tags exist", "no tags")


def section(heading: str) -> str:
    start = README.index(heading)
    following = re.search(r"^## ", README[start + 1:], re.MULTILINE)
    return README[start:start + 1 + following.start()] if following else README[start:]


def changelog_dates() -> dict[str, str]:
    return dict(re.findall(r"^## \[([^\]]+)\] - (\d{4}-\d{2}-\d{2})", CHANGELOG, re.MULTILINE))


def test_the_readme_keeps_the_sections_it_promises_in_order():
    positions = [README.index(heading) for heading in REQUIRED_HEADINGS]
    assert positions == sorted(positions)
    assert all(README.count(f"\n{heading}\n") == 1 for heading in REQUIRED_HEADINGS)


def test_every_test_file_the_readme_names_exists_and_every_named_function_is_in_it():
    named = set(re.findall(r"`(tests/test_\w+\.py)(?:::(\w+))?`", README))
    assert named, "the README names no tests"
    for path, function in named:
        source = (REPO / path).read_text(encoding="utf-8")
        if function:
            assert re.search(rf"^\s*def {function}\(", source, re.MULTILINE), f"{path}::{function}"


def test_every_test_function_the_readme_names_alone_exists_somewhere():
    everything = "\n".join(TESTS.values())
    functions = set(re.findall(r"`(test_\w+)`", README))
    assert functions, "the README names no test functions"
    for function in functions:
        assert re.search(rf"^\s*def {function}\(", everything, re.MULTILINE), function


def test_every_version_and_date_in_the_ledger_matches_the_changelog():
    ledger = section("## WHAT BROKE AND HOW IT WAS FIXED")
    dates = changelog_dates()
    entries = re.findall(r"^\*\*(\d+\.\d+\.\d+)\*\* \((\d{4}-\d{2}-\d{2})(?:, history line (\d{4}-\d{2}-\d{2}))?\)",
                         ledger, re.MULTILINE)
    assert entries, "the ledger has no entries"
    assert len(entries) == len(re.findall(r"^\*\*", ledger, re.MULTILINE)), "an entry is not in the checked form"
    history = CHANGELOG.split("## [0.1.0]", 1)[1]
    for version, date, history_date in entries:
        assert dates.get(version) == date, f"{version}: README says {date}, CHANGELOG says {dates.get(version)}"
        if history_date:
            assert version == "0.1.0" and f"- {history_date}:" in history, history_date
    order = [tuple(int(n) for n in version.split(".")) for version, _, _ in entries]
    assert order == sorted(order), "the ledger is in the order it happened"


def test_every_ci_job_the_readme_names_is_in_the_workflow():
    jobs = set(re.findall(r"`(static|pytest|integration)`", README))
    assert jobs == {"static", "pytest", "integration"}
    for job in jobs:
        assert re.search(rf"^  {job}:", WORKFLOW, re.MULTILINE), job


def test_the_readme_uses_no_marketing_words():
    lowered = README.lower()
    assert not [word for word in BANNED_WORDS if word in lowered]


def test_the_readme_has_no_em_dashes():
    assert chr(0x2014) not in README and chr(0x2014) not in CHANGELOG


def test_the_readme_says_nothing_about_whether_release_tags_exist():
    lowered = README.lower()
    assert not [phrase for phrase in TAG_STATE_PHRASES if phrase in lowered]


def test_the_warden_release_the_readme_names_is_the_one_the_pin_comment_names():
    named = re.search(r"\(the pin is (\d+\.\d+\.\d+)\)", README)
    assert named, "the README no longer names the pinned Warden release"
    pin_line = next(line for line in PYPROJECT_TEXT.splitlines() if line.lstrip().startswith('"warden @ '))
    assert f"Warden {named.group(1)}" in pin_line, (named.group(1), pin_line)


def test_the_history_start_date_the_readme_states_is_in_the_changelog():
    stated = re.search(r"history in `CHANGELOG.md` starts on (\d{4}-\d{2}-\d{2})", README)
    assert stated, "the README no longer states when the history starts"
    history = CHANGELOG.split("## [0.1.0]", 1)[1]
    first = min(re.findall(r"^- (\d{4}-\d{2}-\d{2}):", history, re.MULTILINE))
    assert stated.group(1) == first


def test_the_cns_pin_in_the_readme_note_is_the_pin_in_pyproject():
    tag = re.search(r"to `(v\d+\.\d+\.\d+)` in \d+\.\d+\.\d+\. Drafter imports only", README)
    assert tag, "the README no longer carries the CNS migration note"
    pyproject = tomllib.loads(PYPROJECT_TEXT)["project"]["dependencies"]
    assert any(d.startswith("cns @ ") and d.split("#")[0].strip().endswith(f"@{tag.group(1)}") for d in pyproject)


def test_the_stack_page_does_not_call_a_public_repository_private():
    stack = (REPO / "STACK.md").read_text(encoding="utf-8")
    assert "CNS (private)" not in stack


#: What the self-hosting record says about this repository. Copied from the CNS repository's
#: docs/evidence/SELFHOSTING_2026-10-23.md (branch claude/horsemen-production-status-5wsndb until merged), rows
#: "DRAFTER run 1" and "DRAFTER run 2". The README quotes them; this test holds the quotes to these constants so a
#: number cannot be changed in the README without changing it here, where the evidence file is named.
SELFHOSTING_EVIDENCE = "docs/evidence/SELFHOSTING_2026-10-23.md"
SELFHOSTING_RECORDED = (
    "383 passed and 10 failed",          # run 1: FINISH_REJECTED, SUITE_RED, ghost_tools in site-packages
    "393 passed, 0 skipped",             # run 2: ACCEPT, the Judge's own words
    "37 findings at the start and 37 at the end",    # Ghost, none new
    "28 of 28 attacks held",             # SWIZZLE governor attacks
    "5 of 7 failure modes",              # ASSAY's answer key, floor 3
    "floor of 3",
    "7 gaps",                            # the seven declined checks, in both runs
    "Ghost still reports 37 findings",
    "`FINISH_REJECTED`", "`ACCEPT`",
    "Burnish 0.3.11",
)
DECLINED_CHECKS = ("mutate", "kernel", "structure", "tests", "project", "secrets", "correlate")


def test_the_self_hosting_paragraph_holds_the_numbers_in_the_evidence_record():
    text = section("## SELF-HOSTING")
    assert SELFHOSTING_EVIDENCE in text
    assert "claude/horsemen-production-status-5wsndb" in text and "https://github.com/wking53214/CNS" in text
    for quoted in SELFHOSTING_RECORDED:
        assert quoted in text, quoted
    for check in DECLINED_CHECKS:
        assert f"`{check}`" in text, check
    assert "does not mean there are no secrets, no weak tests" in text
    assert "no fresh" not in text.lower(), "the stale 'no fresh run is recorded' sentence came back"


def test_the_readme_says_the_ci_sibling_pins_are_a_tested_set_not_a_head_of_main():
    assert "the last set this repository's CI tested on its own" in README
    assert "`stack` job in the CNS repository" in README
    lowered = " ".join(WORKFLOW.lower().replace("#", " ").split())
    assert "head of" not in lowered and "heads of" not in lowered, "the workflow calls a pin the head of something"
    assert "they are not moved when warden's pin moves" in lowered
