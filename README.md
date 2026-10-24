# Drafter

*Formerly Proposer. Renamed in October 2026; the role is unchanged.*

The in-loop maker. It reads what Ghost Tools found and proposes one fix at a time. It writes none of the files it proposes to change.

## WHAT THIS IS

Drafter is one of seven repositories in a stack that improves code under human control. Given a finding from Ghost Tools (a code scanner), it returns the change that would close it, as data: a list of file edits with the old and the new text. [Warden](https://github.com/wking53214/Warden) runs the loop around it. Warden asks Drafter for a change, checks that a person granted it, runs the target's tests, applies the change, runs the tests again, and has Ghost look again. Drafter is then asked again, until it has nothing left to propose.

It is small and young. It has three fixers, it has been tested on scratch repositories and not on large real code, and the sections below say plainly what is and is not shown.

Version `0.2.11`. Python 3.11 or newer. It depends on Warden for the shapes of a proposal and on CNS for the shared rows (`Defect`, `FileEdit`), and on nothing else. Warden is pinned to a full commit and CNS to its release tag in `pyproject.toml`, which is the one place the pins are written; see "Bumping the pins" below.

## HOW TO INSTALL AND RUN

### Install

You need Python 3.11 or newer and git (pip fetches Warden and CNS from GitHub). The bare names `drafter`, `warden` and `cns` on PyPI belong to other, unrelated projects, so never run `pip install drafter` (or `warden`, or `cns`). Install from a checkout of this repository:

```bash
python3 -m venv .venv
.venv/bin/pip install -e '.[dev]'
.venv/bin/pip check
.venv/bin/pytest -q -rs
```

That installs Drafter and the exact Warden commit and CNS tag named in `pyproject.toml` (`dependencies`). `pip check` should print "No broken requirements found." On a machine without the rest of the circuit the last command skips the tests that need it, and says why for each skip; see "What works" for how CI runs them all.

To install the whole circuit with the install file in the CNS repository, which pins every repository (this one included) to the commits it names:

```bash
python3 -m venv .venv && .venv/bin/pip install -r contracts/install-stack.txt
```

Run that from a checkout of CNS on its `main` branch, which holds the install file. The `drafter @` line in the file says which commit of this repository it installs; that can be older than the checkout you are reading, because the file is re-pinned by hand. This README names no commit of this repository, because a commit cannot name itself. Installing this package alone from a release tag, `git+https://github.com/wking53214/DRAFTER.git@<tag>`, is the intended form for a tagged release; it has not been tried here, so use a checkout or the install file. Do not install this package alone from `main`: `main` moves, and nothing there says it was tested with the other repositories.

CNS note: the CNS pin moved from `v1.9.0` to `v2.0.0` in 0.2.10. Drafter imports only the `Defect` and `FileEdit` rows from CNS (`cns.defect`, `cns.seat`); `cns.stack.StackPin`, the one CNS 2.0.0 item that now requires a full commit, is not imported here.

### Bumping the pins

This package depends on one exact Warden commit and one exact CNS release tag, so a change on either's `main` cannot break it without anyone noticing. To move to a newer one:

1. For Warden, pick the full 40-character commit you want, and note the release it corresponds to. For CNS, pick the release tag, written exactly as Warden writes it (a tag URL and a commit URL are two sources to pip).
2. Put it after the `@` in the matching line of `pyproject.toml`, with the release in a trailing comment.
3. Run `pip install -e ".[dev]"`, `pip check` and `pytest`. The tests check that the Warden pin is a tag or a full commit, that its comment names the installed release, that the README names the same Warden release, that the CNS pin is a release tag and the same text Warden requires, and that this package's `requires_contract` matches the installed Warden's `CONTRACT`.
4. Open a pull request. CI runs the same checks, and the `integration` job runs the whole suite against the circuit.

The `integration` job also pins its four sibling checkouts (ghost_tools, JUDGE, SWIZZLE, ASSAY) to full commits; bump them in `.github/workflows/tests.yml` the same way.

### Run

Warden loads it:

```bash
warden tagteam PATH --drafter drafter.seat:Drafter --authorize ACTOR --reason TEXT --ghost-root GHOST_TOOLS
```

For a person who wants to see what it would propose without running the loop, there is a read-only dry run:

```bash
drafter --version
drafter propose PATH --findings ghost.json     # findings from a saved Ghost JSON report
drafter propose PATH --ghost-root GHOST_TOOLS  # or Warden's own read-only Ghost scan, which needs a named root
drafter propose PATH ... --scope documentation # as Warden sets it from the grant
drafter propose PATH ... -v                    # -v logs INFO to stderr, -vv adds refusals and tracebacks
```

With neither `--findings` nor `--ghost-root` there is nothing to read findings from: Warden 0.13.2 and later refuse a Ghost scan with no named root (an installed Ghost Tools never stands in for one), and the command exits 3 and says so. Warden 0.13.4 and later (the pin is 0.13.9) also require that root to be a git checkout with a readable version and refuse a site-packages root, so point `--ghost-root` at a clone, not at an installed copy.

It prints one JSON object on stdout: `proposal` (the intent, scope, affected files and every edit with its `old` and `new` text, or `null`) and `skipped` (each finding Drafter recognised but left alone, with the reason). It writes no file. Exit codes:

| code | meaning |
|---|---|
| 0 | a proposal was made |
| 1 | nothing to propose (the JSON still lists why findings were skipped) |
| 2 | usage error: an unknown option (options are not abbreviated: `--finding` is refused), or PATH is empty or not a folder |
| 3 | findings could not be obtained (Ghost could not run, or the findings file is unreadable); this is unknown, never "nothing to propose" |
| 4 | the output pipe was closed before the report was written (for example `drafter propose ... \| head`), or stdout could not take it (a full device, or no stdout at all); one plain line on stderr says which; the report was not delivered, so this is unknown, never "nothing to propose" |

`python -m drafter` is the same command. As a library, Drafter configures no logging; attach a handler to the `drafter` logger to see its warnings.

## HOW IT WORKS

### What it does not own

- Finding problems or counting anything (Ghost Tools). Every number Drafter uses comes from a Ghost finding.
- Writing files, granting permission, running tests, deciding the loop is done (Warden).
- Testing whether the detectors are any good (SWIZZLE).
- The answer key (ASSAY).
- Beautifying the code and writing the final README (Burnish, once, after the loop ends).

### Shape

```text
Ghost finding  ->  Drafter.propose(target, findings, baseline)  ->  Transformation (data)
                                                                         |
                                                    Warden: grant, suite, apply, re-inspect
```

`Drafter.propose` walks the findings in order. For each one it looks up a fixer by Ghost's detector name. The first fixer that can close its finding safely returns an edit, and Drafter wraps it as a proposal. If no fixer can, it returns `None`, which is how it says it has nothing left. That is not a claim the tree is clean: Ghost may still report findings no fixer here handles. Warden calls `Drafter.propose` once per cycle and stops calling it when it returns `None`.

| module | owns |
|---|---|
| `drafter.seat` | the `Drafter` class Warden calls |
| `drafter.fixers` | the table from Ghost detector name to fixer |
| `drafter.fixers.doc_test_count` | the answer to `doc_test_count_drift` (a stale "N tests passed" claim) |
| `drafter.fixers.dead_code` | the answer to `dead_code` (a function or class nothing uses) |
| `drafter.fixers.list_membership` | the answer to `list_membership_in_loop` (a module-level list scanned on every pass of a loop; its brackets become a set's) |
| `drafter._safe` | path, file-reading and number checks every fixer shares |
| `drafter._pyblock` | the plain-text check that a line range is exactly one definition |

### Rules the code follows

- **One intentional change per proposal.** Several findings mean several turns of the loop.
- **Ghost's facts, not Drafter's.** A fixer takes the claim, the lower bound, the line, the name and the `writable` flag from the finding. It never counts tests or decides what is unused.
- **Safe, and never silent about a surprise.** A fixer returns nothing rather than guess. Every refusal also writes a plain-language reason into `Drafter.last_skipped`, a list of `(finding id, reason)` for the latest call. `Drafter.describe_skipped()` returns the same list as readable lines; Warden reads it after every call and prints the lines as `drafter_skipped` in its JSON (a capped list), so a person can see why a finding was left alone. A record that names no detector (missing, empty or not text) is listed too, so it cannot pass for a clean tree; a finding for a detector with no fixer here is still not listed. In `drafter propose`, a record whose fields have the wrong type is listed as "could not be read" and the records after it are still read. A deliberate refusal is not an error. An exception nobody meant to raise is: it is caught only at the boundaries that must not crash the loop (the fixer wrapper in `drafter._safe.run_fixer`, the call into a pluggable fixer, the reading of a hostile finding), and there it is recorded as `internal error (ExceptionType: message)` in the same list and logged at WARNING on the `drafter` logger (traceback at DEBUG). Where the exception type is knowable (a malformed finding, a mismatch with Warden while building the proposal) only those types are caught; anything else propagates to Warden instead of passing for a quiet "no safe fix".
- **Finding the file.** The path in a finding is tried as given under the target. Only if no such file exists is a leading folder equal to the target's own name removed (older Ghost output spelled a root-level file as `tgt/m.py`). The file must be a real file inside the target: no `..`, no symlink on the way, not under `tests`, `.git`, `.venv` or `.github`, and not a test file or one of these by name (any folder, any letter case): `conftest.py`, `pyproject.toml`, `pytest.ini`, `tox.ini`, `setup.cfg`, `setup.py`, `noxfile.py`, `.coveragerc`, `Makefile`, `MANIFEST.in`, and `requirements*.txt`. The current fixers only rewrite Python and Markdown files, so the non-Python names are blocked as a precaution for a later fixer; `setup.py` is the one that was reachable and was missing.
- **Checking Ghost's lines.** Before proposing to remove code, Drafter reads the file as plain text (it may not use a Python parser) and requires that Ghost's lines are exactly one `def`, `async def` or `class` at the left edge, running to where Ghost says it ends. Anything odd is refused: a body on the header line, tabs mixed with spaces, a backslash line continuation, a multi-line string with text at the left edge, a second definition of the same name, or the name used as a decorator.
- **Smallest possible document edit.** Only the claim phrase (the number, "tests", and a following "passed", "passing" or "collected") is replaced. The rest of the line is untouched. A leading BOM and the file's line endings are kept.
- **Same input, same answer.** Drafter keeps no memory between calls. It does not loop on its own: once a fix is applied Ghost stops reporting the finding, and Warden also stops if a proposal repeats.
- **No writes to your files.** No file of the user's or of the target is written or changed. The one place the package opens anything for writing is `_silence_stdout` in `drafter/cli.py`, an error path that opens the null device (`os.devnull`) so that a report that could not be delivered cannot raise again when the interpreter flushes stdout at exit. `test_the_drafter_never_opens_a_file_for_writing` reads the syntax tree of every module and fails on any other call that opens a file for writing or changes the filesystem; that one site is named in its allowlist.
- **Conservative removal.** Ghost's "dead" means no syntax node names the function. Drafter also declines (and records why in `describe_skipped`) when Ghost's `dynamic_lookup_possible` is anything but `no`; when the name appears anywhere in the repository outside its own definition (a string, an attribute, an `__all__`, a `.pyi` stub, a config or docs file, an import or re-export, `TYPE_CHECKING`); when a file in the same package looks things up by a computed name or glues a piece of the name onto a quoted prefix or suffix; when the module is star-imported; when it carries any decorator (a call or attribute form is treated as registering); or when it has a dunder, protocol, abstract, property or overload role. A call inside `try/except` is not evidence of safety.
- **Test-count claims.** Only the project's root README is rewritten, and only when the sentence reads as this project's own suite. Sub-package READMEs, other documents, "upstream has N tests", "added N tests", "before the fix, N tests failed", platform or version phrases, and a count followed by "failed", "skipped" or "errors" are declined.
- **List to set, only when nothing can tell.** For `list_membership_in_loop`, Ghost names the container, says whether the literal is a list or a tuple, and gives the line it is defined on. The fixer reads the file's tokens (the standard library's tokenizer, which builds no syntax tree and decides nothing) and changes the literal's two brackets to braces, nothing else. It refuses unless the literal sits at column 0, is bound exactly once, holds only plain hashable literals (strings that are not f-strings, whole or decimal numbers, `None`, `True`, `False`), is used in the same file only in membership tests (`in`, `not in`; never iterated, indexed, measured, concatenated, called, rebound or exported), and is mentioned in no other file of the repository, not even in a string or a document.
- **Scope.** Every proposal carries `scope_hint` (`"code"` or `"documentation"`), and `Drafter.scope_of(finding)` answers the same from the detector name alone, with no file reads. `Drafter(scope="documentation")` tries in-scope findings first and skips the rest. Warden sets `scope` from the human grant before the first call (Warden 0.11.0 or newer), so under a documentation grant the dead-code fixer is skipped with a reason instead of being proposed and declined.

### Boundaries

Drafter's modules import the standard library, themselves, and exactly these others: `warden.models` (the proposal shape, `defects_from_ghost`), `cns.defect` and `cns.seat` (the shared `Defect` and `FileEdit` rows), and, in the command line only, `warden.ghost` (Warden's own reader of Ghost's JSON and its read-only Ghost scan). It does not import Burnish, Ghost Tools, SWIZZLE, ASSAY or the Judge, and it does not use `ast`, `subprocess` or `importlib`. `tests/test_independence.py` enforces this as an allowlist: any other import fails the test, and so does an allowed name nothing uses, so this paragraph cannot drift.

## WHAT WORKS

Each line names what shows it. Test totals are not written here, because a number in prose goes stale; run `pytest -q -rs` to see the current ones and the reason for every skip.

- A stale "N tests passed" claim is rewritten to say "at least M `test_*` functions (an earlier version of this document gave N)", using Ghost's M, and nothing else on the line changes. Shown by `tests/test_doc_claims.py` (for example `test_only_the_claim_phrase_changes`).
- The claim is refused, with a reason, inside a link, image, URL, backticks, HTML tag, comment or front matter; inside a code fence or indented code; on a heading (including a setext heading), in a table row; in `CHANGELOG`, `HISTORY`, `NEWS` or `RELEASES` files; when the number looks like part of a version such as 3.10; when the digits are not plain ASCII; and when Ghost's lower bound is not above the claim. Shown by the same file (`test_a_claim_in_the_wrong_place_is_refused_with_a_reason`, `test_structure_that_a_rewrite_would_damage_is_refused`, `test_changelog_style_files_are_refused`).
- Dead code is proposed for removal only when Ghost's lines match the text exactly. Cases where a span runs into the next function, stops mid-body, or leaves a decorator behind are refused or handled. Shown by `tests/test_dead_code_spans.py`; the computed-lookup, re-export, stub, `TYPE_CHECKING` and registering-decorator cases are shown by `tests/test_conservative.py`.
- A root-level file reported as `tgt/m.py` is found. Shown by `tests/test_paths.py` and `tests/test_real_ghost.py`.
- Odd input (a file that is not UTF-8, missing or wrong-typed fields, junk instead of findings, a bad target) gives no proposal and a reason, never a crash. Shown by `tests/test_odd_input.py`.
- A module-level list of strings tested with `in` inside a loop becomes a set, byte for byte otherwise (a tuple too; a multi-line literal with comments, CRLF and a BOM all kept). Every other kind of element (an f-string, a name, a tuple, a hex number, implicit concatenation) and every other kind of use (iteration, indexing, `len`, concatenation, a method, a rebinding, a keyword argument, a mention in a string, another file or a document) is refused with a reason. An old Ghost that does not name the container gets no proposal. Through the whole gate the set stands and Ghost falls silent. Shown by `tests/test_list_membership_fixer.py` (`test_through_the_whole_gate_the_set_stands_and_ghost_is_silent` needs the real circuit; the rest do not).
- With the real Ghost scan and the real Warden loop, a root-level module, a nested module, a module several folders deep and two README claims (one in the root, one in a subfolder) each produce a proposal that Warden applies cleanly, and the loop then converges and ends `ACCEPT`. Through the whole gate the set stands and Ghost falls silent. Shown by `tests/test_real_ghost.py` (`test_the_real_loop_fixes_the_root_readme_only_and_converges`, `test_a_real_dead_code_finding_is_proposed_and_applied_cleanly`) when Ghost Tools, SWIZZLE, ASSAY and the Judge are importable; the CI job `integration` runs them and fails if any test skips.
- A run that ends `ACCEPT_UNVERIFIED` has the applied edit put back by Warden. Shown by `tests/test_real_ghost.py::test_an_unverified_run_puts_the_applied_edit_back`.
- The exit codes are the documented ones, including exit 4 for a closed pipe, a full device and a closed stdout. Shown by `tests/test_cli.py` (`test_exit_codes_are_the_documented_ones`, `test_python_dash_m_drafter_with_stdout_on_a_full_device_exits_4_cleanly`, `test_python_dash_m_drafter_into_a_closed_pipe_exits_4_cleanly`).
- A bug inside a fixer is reported on the `drafter` logger and in the JSON, not swallowed. Shown by `tests/test_observable_failures.py`.
- Drafter declares `requires_contract = "1"` and Warden loads it with no contract warning. Shown by `tests/test_contract.py`.
- It imports only the modules named under "Boundaries", writes no file of the user's (apart from the null-device error path described under "Rules the code follows"), never counts. Shown by `tests/test_independence.py` (`test_the_drafter_never_opens_a_file_for_writing`).
- The pins agree: the Warden pin comment names the installed Warden release, and the CNS pin text equals the text Warden itself requires. Shown by `tests/test_warden_pin.py` (`test_the_cns_pin_text_equals_wardens_own_cns_requirement`).
- Seated in the whole circuit (Ghost, SWIZZLE, ASSAY, Judge and Burnish all live, through `warden tagteam --stack`), a dead function was commented out under a `code` grant and skipped with a reason under a `documentation` grant, and both runs ended `ACCEPT`, exit 0. Shown by a hand run on scratch repositories on 2026-10-14, recorded in Warden's `docs/REGISTRY.json` (row 3 holds the two runs; row 4 added the list fixer). It was a hand run with an early Drafter (0.1.0) and an early Warden (0.11.0). No test or CI job here repeats it: `tests/test_real_ghost.py` runs a similar gate with Ghost, SWIZZLE, ASSAY and the Judge, but without Burnish and not through `--stack`.
- CI runs three jobs: `static` (`ruff check .` and strict `mypy`, both gates), `pytest` (the fast standalone run on Python 3.11, 3.12 and 3.13) and `integration` (the whole suite on the same three Pythons with the four siblings checked out at the full commits written in `.github/workflows/tests.yml`, and a step that fails the job if even one test skips). `tests/test_release.py` holds the workflow to full-commit pins.

Without Ghost Tools on the import path, the tests that need the real Ghost scan skip with the reason "the real Ghost scan needs ghost_buster on PYTHONPATH". The tests that run the full gate also need SWIZZLE and ASSAY checkouts beside this one (folder names matched without regard to case, or point `CIRCUIT_ROOT` at the folder that holds them) and the Judge importable, and skip and say so otherwise. ASSAY's answer key also needs numpy and matplotlib installed wherever it is graded (the `integration` job installs `matplotlib==3.11.2` and, per interpreter, `numpy==2.4.6` on Python 3.11 or `numpy==2.5.4` on 3.12 and 3.13, because numpy 2.5 requires Python 3.12 or newer; ASSAY 0.11.1 exits 1 when a claim is skipped). Nothing else skips.

Drafter's tests import Warden from the import path, so they run against whatever the install resolved, which is the commit pinned in `pyproject.toml`. A Warden without the held-result rule fails `tests/test_real_ghost.py::test_an_unverified_run_puts_the_applied_edit_back`; the pin carries it.

## WHAT DOES NOT WORK / NOT PROVEN

Does not work:

- Only three kinds of finding can be fixed: `doc_test_count_drift`, `dead_code` and `list_membership_in_loop`. Every other Ghost detector is ignored.
- Only Markdown files are rewritten for claims, and only `.py` files for dead code and list membership.
- The list fixer needs a Ghost that reports `name`, `container` and `defined_at` on the finding (ghost_tools after 1.9.1). An older Ghost's finding gets no proposal and a reason.
- A document claim split across two lines is skipped, as is a claim that is not below Ghost's lower bound (no edit is made when the number is not an undercount).
- Ghost does not report a decorated function as dead (it counts a decorator as a use), so the decorator handling is exercised by hand-built findings only.
- Drafter has no service or output file of its own. Inside Warden, the reasons it stayed silent reach a person through Warden's `drafter_skipped` field. Outside it, the `drafter propose` dry run prints them in full, and the `drafter` logger carries warnings for real errors.

Not proven:

- A run against a large real repository. The end-to-end tests use small scratch repositories, and so does the recorded circuit run.
- That the text-level definition check agrees with a real parser on every possible Python file. It is stricter than Python on purpose and refuses when unsure, and Warden's keep test and comment-out test remain the real gate. But it was written and tested by hand, not checked against a large body of real code.
- Python's newer f-string rules (quotes reused inside braces) can confuse the small scanner. The likely result is a refusal, not a wrong edit, but this is not proven.
- That an edit Drafter proposes is correct. Drafter does not run anything. A proposal is only as good as Ghost's finding and the refusals above, and the check that it did no harm is Warden's: the target's own tests before and after, and Ghost looking again.
- Any run of the whole circuit with the current versions. The only recorded run is the old one named under "Self-hosting".
- Behaviour on macOS or Windows. CI uses `ubuntu-latest` only.

More fixers would be added only for a Ghost detector whose finding has a safe mechanical answer.

## KNOWN DEFECTS

Open ones, with what they cost:

- A list item or paragraph nested four or more spaces deep is refused as if it were a code block, even when it is a nested list. This costs a missed fix, not a wrong one. (The refusal of indented text is held by `test_structure_that_a_rewrite_would_damage_is_refused`; the nested-list case has no test of its own.)
- The list fixer cannot see what is on the left of `in`. Against a list, `x in NAME` is False for an unhashable `x`; against a set it raises `TypeError`. If a caller ever passes a list or a dict there, the fixed code crashes where the old code was silently False, and only a test that exercises that call will catch it. Found by red team on 2026-10-14; left as a limit because refusing it would refuse every fix. No test can hold this one.
- A line that has a `|` anywhere is treated as a table row and refused. This costs a missed fix.
- The claim wording changes the meaning slightly on purpose: "N tests passed" becomes "at least M `test_*` functions", because Ghost counts test functions and does not run them. Where the claim began a sentence, the sentence starts "The suite holds"; elsewhere it reads "at least M ...". Odd sentences can still read a little stiffly.
- The text scanner and the Markdown checks are hand-rolled, so they are long, and a long hand-written scanner is where the next bug is most likely to be.

## WHAT BROKE AND HOW IT WAS FIXED

In the order it happened. Each line gives the version that fixed it (with the date of that CHANGELOG heading), what was wrong, and what now keeps it from coming back. This list was checked against `CHANGELOG.md`, the git history and the tests; where the fix was wrong or overstated the first time, it says so.

**0.1.0** (2026-10-16, history line 2026-10-09): A red-team pass on the first version found that a root-level file reported by Ghost as `tgt/m.py` was not found, that dead-code spans could run into the next function, that a document edit replaced more than the claim, and that odd input could crash it. Fixed by looking up the path as given and then without the target's folder name, checking spans as plain text, replacing only the claim phrase, and recording a reason instead of raising. Held by `tests/test_paths.py`, `tests/test_dead_code_spans.py`, `tests/test_doc_claims.py` and `tests/test_odd_input.py`.

**0.1.0** (2026-10-16, history line 2026-10-10): Dead-code removal and test-count edits were still too eager after that pass. Fixed by declining on any sign the name could be reached another way (a string, an attribute, `__all__`, a stub, a re-export, a computed lookup, a decorator) and by rewriting only the root README. Held by `tests/test_conservative.py`.

**0.1.0** (2026-10-16, history line 2026-10-12): The loop tests asserted that the decision started with `ACCEPT`, which also matches `ACCEPT_UNVERIFIED`, and they ran without SWIZZLE, ASSAY, a git repository or the Judge, so they could never reach a real `ACCEPT`. Fixed by building the real gate in the tests and requiring the decision to equal `ACCEPT`. Held by `test_the_real_loop_fixes_the_root_readme_only_and_converges` and `test_an_unverified_run_puts_the_applied_edit_back`. The same day the README's counts, version pins and install commands were found not to match the code and the test results and were corrected; the guard that came later is `test_the_readme_hard_codes_no_test_totals` (the README had stated one total and then a different one).

**0.1.0** (2026-10-16, history line 2026-10-14): The list fixer accepted `x in NAME == y`, where a set does not compare equal to a list; it now refuses a membership test followed by a comparison. Held by `test_any_other_use_in_the_file_is_refused`. The full-gate tests skipped when the sibling clones were named `SWIZZLE` and `ASSAY` in capitals; the lookup now ignores case. No test of its own; the `integration` job fails on any skip, which would show it.

**0.1.0** (2026-10-16, history line 2026-10-15): On Python 3.11 the list fixer proposed an edit to a file it could not read, because before 3.12 the tokenizer does not raise on an unclosed string. Found when its own test failed on 3.11. Held by `test_a_file_that_will_not_tokenize_is_left_alone`.

**0.2.0** (2026-10-17): mypy errors in six files and two `noqa` comments that suppressed nothing. Now `ruff check .` and strict `mypy` are CI gates (the `static` job). The README also restated a Warden pin the code had long left; it no longer does, and `test_the_readme_does_not_restate_the_pinned_versions` holds that.

**0.2.2** (2026-10-17): The `integration` job pinned JUDGE to a commit whose version did not match the comment beside it, and the README install line installed `main`, which then had no command line. Both corrected; every GitHub Action is pinned to a full commit. Held by `test_the_workflow_sibling_checkouts_are_pinned_to_full_commits`, `test_every_workflow_action_is_pinned_to_a_full_commit_with_its_tag` and `test_the_readme_install_section_makes_no_false_commit_claim`. Nothing checks that the version comment beside a sibling pin is true; no test yet.

**0.2.3** (2026-10-21): Warden 0.13.2 refuses a Ghost scan with no named root, but Drafter's help and README still described a default scan. `drafter propose PATH` with neither option exits 3. Held by `test_a_scan_with_no_ghost_root_is_refused_by_warden_and_is_exit_3` and `test_a_ghost_root_that_does_not_hold_the_package_is_exit_3`.

**0.2.4** (2026-10-21): The `integration` job went red on Python 3.11. It had installed `numpy==2.5.4` on every leg (added in 0.2.3), and numpy 2.5 needs Python 3.12 or newer. Fixed with a pin per interpreter. Held by `test_the_integration_numpy_pin_covers_every_python_in_its_matrix`. In the same release: the README install section named a commit as the one the circuit had tested, which a commit cannot do (`test_the_readme_install_section_makes_no_false_commit_claim`); `drafter propose ... | head` ended in a `BrokenPipeError` traceback and exit 1, which reads as "nothing to propose", and now exits 4 (`test_a_closed_output_pipe_is_exit_4_with_a_message_not_a_traceback`); and an abbreviated option such as `--finding` silently meant `--findings`, and is now a usage error (`test_an_abbreviated_option_is_a_usage_error_not_a_guess`).

**0.2.6** (2026-10-21): The README said Warden 0.13.3 first refused a scan with no root; it was 0.13.2. Text only; no test yet.

**0.2.8** (2026-10-21): A finding record with no usable detector, or a record whose fields had the wrong type, ended with exit 1 and an empty `skipped` list (or a traceback), so the report could not say why. Both are now listed with a reason, and the records after a bad one are still read. Held by `test_a_record_with_no_usable_detector_is_skipped_with_a_reason`, `test_a_record_of_the_wrong_shape_is_skipped_not_a_traceback` and `test_a_bad_record_does_not_stop_the_good_one_after_it`. The README also still told readers to use a CNS branch "until that is on main", and the 0.2.7 CHANGELOG entry named a renamed test by its old name; both were corrected. This release also said the exit-code table "stays true", which 0.2.9 showed was not the whole story.

**0.2.9** (2026-10-22): A report that could not be written to stdout (a full device, or no stdout) ended as a traceback with exit 1, the code that means "nothing to propose"; only a closed pipe had been handled. These now exit 4, and `drafter propose ""` no longer silently uses the current directory (exit 2). Held by `test_a_full_stdout_is_exit_4_with_one_plain_line_not_a_traceback`, `test_a_closed_stdout_is_exit_4_with_one_plain_line_not_a_traceback`, `test_python_dash_m_drafter_with_stdout_on_a_full_device_exits_4_cleanly` and `test_an_empty_path_is_a_usage_error_not_the_current_folder`.

**0.2.10** (2026-10-22): `STACK.md` called CNS private although it is public, and the README had no plain account of what was unproven or what had broken, and carried a claim of beauty that nothing could show. `STACK.md` is corrected and the README rewritten; the CNS pin moved to its v2.0.0 tag with Warden and the sibling checkouts moved to match. Held by `test_the_stack_page_does_not_call_a_public_repository_private` and the other tests in `tests/test_readme_ledger.py`.

## SELF-HOSTING

The circuit has been pointed at its own repositories once that is recorded. Warden's `docs/REGISTRY.json`, rows 5 and 6 (dated 2026-10-14 in the file), record the seven repositories being governed as fresh clones, Drafter's among them. For this repository the record is row 5: it ended `ACCEPT` with one change applied to the clone, and the file says the change was Burnish's generated facts section in the README and that nothing was committed from the clones. Row 6 repeated the run for four other repositories and does not include this one.

That run predates Warden 0.13.0 and the stricter rules Warden has had since, so it does not show what the current versions would do. No fresh run on the current commits is recorded yet. The CNS repository is at https://github.com/wking53214/CNS.

## CEILINGS CODE CANNOT FIX

- The repository is young. Its history in `CHANGELOG.md` starts on 2026-10-08.
- One person maintains it. No outside users are known, so nobody has yet run it on code its author did not choose.
- Releases are tagged by the owner, so check the repository's tags and releases for what exists.
- Experimental, version 0.2.11, maintained by one person. Changes are listed in `CHANGELOG.md`.
- Every test here uses scratch repositories or fixtures. Only use on a large, real codebase would show how often the refusals fire and whether the text checks hold up, and that has not happened.
- The dependencies are git URLs pinned to commits, not releases from PyPI, so installing needs GitHub to be reachable.

## Support

Open an issue at https://github.com/wking53214/Drafter/issues.

## Contributing

Welcome, narrowly. A new fixer must answer a Ghost detector whose finding has a safe mechanical fix, must return nothing when unsure, and must come with a test that shows both.

## License

Apache-2.0. See `LICENSE`.
