"""Release hygiene: one version, said the same everywhere, and no hard-coded test totals in the docs."""

import re
import shlex
import tomllib
from importlib import metadata
from pathlib import Path

import drafter

REPO = Path(drafter.__file__).resolve().parent.parent
PYPROJECT = tomllib.loads((REPO / "pyproject.toml").read_text(encoding="utf-8"))
README = (REPO / "README.md").read_text(encoding="utf-8")
CHANGELOG = (REPO / "CHANGELOG.md").read_text(encoding="utf-8")
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
    # An [Unreleased] heading may sit above the current version, and nothing else may.
    assert headings[headings[0] == "Unreleased"] == drafter.__version__, headings
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
    # No commit at all, this repository's own included: a commit cannot name itself.
    assert not re.search(r"[0-9a-f]{40}", README), "the README restates a full commit; refer to pyproject.toml"
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


def test_the_readme_install_section_makes_no_false_commit_claim():
    """The install section points at the CNS install file (or a release tag) and names no commit of this repository."""
    install = README.split("## Install", 1)[1].split("### Bumping the pins", 1)[0]
    assert "contracts/install-stack.txt" in install
    assert "<tag>" in install, "say how to install once a release tag exists"
    assert not re.search(r"[0-9a-f]{7,40}", install), "the install section names a commit; a commit cannot name itself"
    assert "tested set records" not in README
    assert not re.search(r"^pip install git\+https://github\.com/wking53214/Drafter\.git@", README, re.MULTILINE)


def test_every_workflow_action_is_pinned_to_a_full_commit_with_its_tag():
    uses = re.findall(r"^\s+- uses: (\S+)(.*)$", WORKFLOW, re.MULTILINE)
    assert uses
    for action, comment in uses:
        assert re.fullmatch(r"[\w.-]+/[\w.-]+@[0-9a-f]{40}", action), f"pin {action} to a full commit"
        assert re.search(r"#\s*v\d+\.\d+\.\d+", comment), f"name the tag beside {action}"


def test_the_integration_numpy_pin_covers_every_python_in_its_matrix():
    """numpy 2.5 needs Python 3.12 or newer: a bare `numpy==2.5.4` cannot install on the 3.11 leg."""
    from packaging.requirements import Requirement

    integration = WORKFLOW.split("\n  integration:\n", 1)[1]
    pythons = re.search(r"python-version: \[([^\]]+)\]", integration)
    assert pythons, "the integration job has no Python matrix"
    versions = [v.strip().strip('"') for v in pythons.group(1).split(",")]
    (install,) = re.findall(r"^\s+- run: (pip install .*numpy.*)$", integration, re.MULTILINE)
    requirements = [Requirement(t) for t in shlex.split(install)[2:]]
    numpys = [r for r in requirements if r.name == "numpy"]
    for version in versions:
        applicable = [r for r in numpys if r.marker is None or r.marker.evaluate({"python_version": version})]
        assert len(applicable) == 1, f"Python {version}: need exactly one numpy pin, got {applicable}"
        assert re.fullmatch(r"==\d+\.\d+\.\d+", str(applicable[0].specifier)), applicable[0]
