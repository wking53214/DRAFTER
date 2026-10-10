"""Round-two red-team repros: the Drafter must not remove code something could still reach,
must not rewrite a test count that is not about this project's own suite, and must say which
proposals are in scope.

Each case hands the Drafter a finding that says "framework_hook: no" and "dynamic_lookup_possible: no"
(the most trusting thing Ghost can say), so the Drafter's own checks are what stop it.
"""

import pytest

from support import dead_finding, doc_finding, propose, real_findings

HEAD = "import sys\n\n\n"


def _repo(tmp_path, files):
    root = tmp_path / "tgt"
    root.mkdir(parents=True)
    (root / "pyproject.toml").write_text("[project]\nname='t'\n", encoding="utf-8")
    for rel, text in files.items():
        p = root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text, encoding="utf-8")
    return root


def _dead(root, rel, name="orphan", start=1, end=2, kind="function", **attrs):
    f = dead_finding(file=rel, name=name, start=start, end=end, kind=kind)
    f["attributes"].update(attrs)
    return propose(root, f)


def _declined(tmp_path, files, rel="m.py", **kw):
    root = _repo(tmp_path, files)
    proposal, drafter = _dead(root, rel, **kw)
    assert proposal is None, proposal.edits
    assert drafter.last_skipped
    return drafter.last_skipped[0][1]


ORPHAN = "def orphan():\n    return 1\n"


def test_baseline_a_truly_dead_function_is_still_proposed(tmp_path):
    root = _repo(tmp_path, {"m.py": ORPHAN + "\n\ndef used():\n    return 2\n", "n.py": "from m import used\n\nused()\n"})
    proposal, _ = _dead(root, "m.py")
    assert proposal is not None and proposal.edits[0].old == ORPHAN


@pytest.mark.parametrize("value", ["yes", "maybe", "unknown", ""])
def test_ghosts_dynamic_lookup_flag_declines(tmp_path, value):
    why = _declined(tmp_path, {"m.py": ORPHAN}, dynamic_lookup_possible=value)
    assert "computed lookup" in why


def test_getattr_dispatch_on_the_module_is_declined(tmp_path):
    src = ("import sys\n\n\ndef cmd_orphan():\n    return 1\n\n\ndef run(name):\n"
           "    return getattr(sys.modules[__name__], 'cmd_' + name)()\n")
    assert _declined(tmp_path, {"m.py": src}, name="cmd_orphan", start=4, end=5)


def test_globals_dispatch_is_declined(tmp_path):
    src = "def _cmd_orphan():\n    return 1\n\n\ndef run(x):\n    return globals()['_cmd_' + x]()\n"
    assert _declined(tmp_path, {"m.py": src}, name="_cmd_orphan")


def test_a_prefix_built_lookup_in_another_package_is_declined(tmp_path):
    files = {"pkg/m.py": "def cmd_orphan():\n    return 1\n", "other/run.py": "def go(x):\n    return F[f'cmd_{x}']\n"}
    assert "builds names" in _declined(tmp_path, files, rel="pkg/m.py", name="cmd_orphan")


def test_a_reexport_is_declined(tmp_path):
    files = {"pkg/a.py": "def ok():\n    return 1\n", "pkg/__init__.py": "from .a import ok\n"}
    assert "imported or re-exported" in _declined(tmp_path, files, rel="pkg/a.py", name="ok")


def test_a_star_import_of_the_module_is_declined(tmp_path):
    files = {"a.py": ORPHAN, "b.py": "from a import *\n"}
    assert "star-imports" in _declined(tmp_path, files, rel="a.py")


def test_type_checking_only_use_is_declined(tmp_path):
    files = {"m.py": "class Orphan:\n    x = 1\n",
             "n.py": "from typing import TYPE_CHECKING\n\nif TYPE_CHECKING:\n    from m import Orphan\n\n\ndef f(o: 'Orphan'):\n    return o\n"}
    assert _declined(tmp_path, files, name="Orphan", kind="class")


def test_a_string_annotation_is_declined(tmp_path):
    files = {"m.py": "class Orphan:\n    x = 1\n\n\ndef f(o: 'Orphan') -> 'Orphan':\n    return o\n"}
    assert _declined(tmp_path, files, name="Orphan", kind="class")


def test_a_pyi_listed_function_is_declined(tmp_path):
    files = {"m.py": ORPHAN, "m.pyi": "def orphan() -> int: ...\n"}
    assert ".pyi" in _declined(tmp_path, files)


def test_an_all_entry_is_declined(tmp_path):
    files = {"m.py": '__all__ = ["orphan"]\n\n\n' + ORPHAN}
    assert "__all__" in _declined(tmp_path, files, start=4, end=5)


@pytest.mark.parametrize("rel,text", [("settings.yaml", "handler: orphan\n"), ("cfg.toml", "entry = 'm:orphan'\n"),
                                      ("c.json", '{"h": "orphan"}\n'), ("README.md", "```python\norphan()\n```\n")])
def test_config_and_docs_mentions_are_declined(tmp_path, rel, text):
    assert _declined(tmp_path, {"m.py": ORPHAN, rel: text})


def test_a_string_literal_and_an_attribute_name_are_declined(tmp_path):
    assert "string" in _declined(tmp_path, {"m.py": ORPHAN, "n.py": "NAMES = ['orphan']\n"})
    assert "attribute" in _declined(tmp_path / "b", {"m.py": ORPHAN, "n.py": "import m\nx = m.orphan\n"})


@pytest.mark.parametrize("deco", ["@app.route('/x')", "@click.command()", "@pytest.fixture", "@celery.task",
                                  "@register", "@app.get"])
def test_decorated_handlers_are_declined(tmp_path, deco):
    src = f"{deco}\ndef orphan():\n    return 1\n"
    assert "decorator" in _declined(tmp_path, {"m.py": src}, start=2, end=3)


def test_dunder_protocol_abstract_and_property_roles_are_declined(tmp_path):
    assert "dunder" in _declined(tmp_path, {"m.py": "def __getattr__(n):\n    return 1\n"}, name="__getattr__")
    p = "from typing import Protocol\n\n\nclass Orphan(Protocol):\n    def f(self): ...\n"
    assert _declined(tmp_path / "b", {"m.py": p}, name="Orphan", kind="class", start=4, end=5)
    a = "from abc import ABC, abstractmethod\n\n\nclass Orphan(ABC):\n    @abstractmethod\n    def f(self): ...\n"
    assert _declined(tmp_path / "c", {"m.py": a}, name="Orphan", kind="class", start=4, end=6)
    q = "class Orphan:\n    @property\n    def x(self):\n        return 1\n"
    assert _declined(tmp_path / "d", {"m.py": q}, name="Orphan", kind="class", start=1, end=4)


def test_a_call_inside_try_except_is_not_treated_as_safe(tmp_path):
    files = {"m.py": ORPHAN, "n.py": "def go():\n    try:\n        from m import orphan\n        orphan()\n    except Exception:\n        pass\n"}
    assert _declined(tmp_path, files)


# --- real Ghost -----------------------------------------------------------

def test_real_ghost_repros_all_propose_nothing(tmp_path):
    files = {
        "pkg/__init__.py": "from .a import ok\n",
        "pkg/a.py": "def ok():\n    return 1\n",
        "disp.py": ("import sys\n\n\ndef cmd_start():\n    return 1\n\n\ndef run(name):\n"
                    "    return getattr(sys.modules[__name__], 'cmd_' + name)()\n"),
        "glob.py": "def _cmd_stop():\n    return 1\n\n\ndef run(x):\n    return globals()['_cmd_' + x]()\n",
        "tc.py": "from typing import TYPE_CHECKING\n\nif TYPE_CHECKING:\n    class OnlyForTypes:\n        x = 1\n",
        "st.py": "def stubbed():\n    return 1\n",
        "st.pyi": "def stubbed() -> int: ...\n",
        "web.py": "import flask\napp = flask.Flask('x')\n\n\n@app.route('/')\ndef handler():\n    return 'hi'\n",
    }
    root = _repo(tmp_path, files)
    findings = [f for f in real_findings(root) if f.get("detector") == "dead_code"]
    assert findings, "Ghost should report something dead for this to mean anything"
    from warden.models import defects_from_ghost
    from drafter import Drafter

    drafter = Drafter()
    assert drafter.propose(root, defects_from_ghost(findings), "base") is None


# --- test-count claims ----------------------------------------------------

def _doc(tmp_path, text, rel="README.md", line=3):
    root = _repo(tmp_path, {rel: text})
    return propose(root, doc_finding(file=rel, line=line))


def test_the_root_readme_with_a_plain_claim_is_still_fixed(tmp_path):
    proposal, _ = _doc(tmp_path, "# T\n\nThe suite: 16 tests passed.\n")
    assert proposal is not None


@pytest.mark.parametrize("sentence", [
    "Upstream has 16 tests passing.",
    "We added 16 tests.",
    "Before the fix, 16 tests passed.",
    "On Linux 16 tests passed.",
    "16 tests passed, 0 failed.",
    "16 tests passed, 2 skipped.",
    "Python 3.16 tests passed.",
])
def test_claims_about_other_things_are_declined(tmp_path, sentence):
    proposal, drafter = _doc(tmp_path, f"# T\n\n{sentence}\n")
    assert proposal is None and drafter.last_skipped


def test_a_sub_package_readme_is_declined(tmp_path):
    proposal, drafter = _doc(tmp_path, "# T\n\nThe suite: 16 tests passed.\n", rel="pkg/README.md")
    assert proposal is None and "root README" in drafter.last_skipped[0][1]


def test_docs_folder_is_declined(tmp_path):
    proposal, _ = _doc(tmp_path, "# T\n\nThe suite: 16 tests passed.\n", rel="docs/guide.md")
    assert proposal is None


# --- scope ----------------------------------------------------------------

def _mixed(tmp_path):
    root = _repo(tmp_path, {"m.py": ORPHAN, "README.md": "# T\n\nThe suite: 16 tests passed.\n"})
    return root, [dead_finding(file="m.py", fid="d1", start=1, end=2), doc_finding(fid="r1")]


def test_every_proposal_carries_a_scope_hint(tmp_path):
    root, findings = _mixed(tmp_path)
    code, _ = propose(root, findings[0])
    doc, _ = propose(root, findings[1])
    assert code.scope_hint == "code" and doc.scope_hint == "documentation"


def test_in_scope_findings_go_first_and_out_of_scope_ones_are_not_even_read(tmp_path):
    from warden.models import defects_from_ghost

    from drafter import Drafter

    root, findings = _mixed(tmp_path)
    drafter = Drafter(scope="documentation")
    proposal = drafter.propose(root, defects_from_ghost(findings), "b")        # dead_code listed first
    assert proposal.scope_hint == "documentation"
    only_code = Drafter(scope="documentation")
    assert only_code.propose(root, defects_from_ghost(findings[:1]), "b") is None
    assert "documentation" in only_code.last_skipped[0][1]


def test_scope_of_is_cheap_and_needs_no_files():
    from drafter import Drafter

    d = Drafter()
    assert d.scope_of({"detector": "dead_code"}) == "code"
    assert d.scope_of({"detector": "doc_test_count_drift"}) == "documentation"
    assert d.scope_of({"detector": "other"}) is None and d.scope_of(7) is None
