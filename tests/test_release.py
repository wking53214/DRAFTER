"""Release hygiene: one version, said the same everywhere, and no hard-coded test totals in the docs."""

import re
import tomllib
from importlib import metadata
from pathlib import Path

import drafter

REPO = Path(drafter.__file__).resolve().parent.parent
PYPROJECT = tomllib.loads((REPO / "pyproject.toml").read_text(encoding="utf-8"))
README = (REPO / "README.md").read_text(encoding="utf-8")
CHANGELOG = (REPO / "CHANGELOG.md").read_text(encoding="utf-8")
INSTALL_LINE = r"^pip install git\+https://github\.com/wking53214/Drafter\.git@[0-9a-f]{40}$"
WORKFLOW = (REPO / ".github" / "workflows" / "tests.yml").read_text(encoding="utf-8")


def test_dunder_version_is_the_pyproject_version():
    assert drafter.__version__ == PYPROJECT["project"]["version"]
    assert re.fullmatch(r"\d+\.\d+\.\d+", drafter.__version__)


def test_an_installed_copy_reports_the_same_version():
    try:
        installed = metadata.version("drafter")
    except metadata.PackageNotFoundError:
        return                                                  # run from a checkout, not installed
    assert installed == drafter.__version__, "reinstall (pip install -e .) so the installed metadata is current"


def test_the_changelog_leads_with_the_current_version():
    headings = re.findall(r"^## \[([^\]]+)\]", CHANGELOG, re.MULTILINE)
    assert headings[0] == drafter.__version__, headings
    assert "Unreleased" not in headings[:1] or headings[1] == drafter.__version__
    assert len(headings) == len(set(headings))


def test_the_readme_states_the_current_version():
    assert re.search(rf"^Version `{re.escape(drafter.__version__)}`", README, re.MULTILINE)
    assert "Experimental, version " + drafter.__version__ in README


def test_the_readme_hard_codes_no_test_totals():
    """A count in prose goes stale (it did: the README said 304, then 306). Say how to get it instead."""
    claims = re.findall(r"\b\d+\s+(?:full-gate\s+|real-Ghost\s+)?tests?\b", README)
    assert claims == [], f"remove or generate these counts: {claims}"


def test_the_readme_does_not_restate_the_pinned_versions():
    """The pin lives in pyproject.toml. A tag or version restated in prose is wrong the day the pin moves."""
    # The one install line may name this repository's own commit; nothing else may.
    prose = re.sub(INSTALL_LINE, "", README, flags=re.MULTILINE)
    assert not re.search(r"[0-9a-f]{40}", prose), "the README restates a full commit; refer to pyproject.toml"
    assert "pinned to Warden tag" not in README and "v0.11" not in README and "0.11.5" not in README
    pyproject_text = (REPO / "pyproject.toml").read_text(encoding="utf-8")
    assert "0.11.5" not in pyproject_text, "the pin comment names a version the pin is not"


def test_the_cns_dependency_is_pinned_to_a_full_commit():
    deps = PYPROJECT["project"]["dependencies"]
    (cns,) = [d for d in deps if d.startswith("cns @ ")]
    assert re.fullmatch(r"cns @ git\+https://github\.com/wking53214/CNS\.git@[0-9a-f]{40}", cns), cns


def test_the_workflow_sibling_checkouts_are_pinned_to_full_commits():
    refs = re.findall(r"^\s+ref: (\S+)", WORKFLOW, re.MULTILINE)
    assert refs and all(re.fullmatch(r"[0-9a-f]{40}", r) for r in refs), refs


def test_the_readme_install_line_is_a_full_commit_pin_of_this_repository():
    """A bare `...Drafter.git` installs `main`, which is an older line than this package."""
    assert re.search(INSTALL_LINE, README, re.MULTILINE), "pin the README install line to a full commit"


def test_every_workflow_action_is_pinned_to_a_full_commit_with_its_tag():
    uses = re.findall(r"^\s+- uses: (\S+)(.*)$", WORKFLOW, re.MULTILINE)
    assert uses
    for action, comment in uses:
        assert re.fullmatch(r"[\w.-]+/[\w.-]+@[0-9a-f]{40}", action), f"pin {action} to a full commit"
        assert re.search(r"#\s*v\d+\.\d+\.\d+", comment), f"name the tag beside {action}"
