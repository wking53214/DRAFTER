# Drafter

*Formerly Proposer. Renamed in October 2026; the role is unchanged.*

The in-loop maker. It reads what Ghost Tools found and proposes one fix at a time. It never writes a file.

## WHAT THIS IS

One of seven repositories in a stack that improves code under human control. Drafter has one job: given a Ghost Tools finding, return the change that would close it, as data. [Warden](https://github.com/wking53214/Warden) runs the loop around it. Warden asks Drafter for a change, checks a person granted it, runs the target's tests, applies the change, runs the tests again, and has Ghost look again. Drafter is then asked again, until it has nothing left to propose.

Version `0.1.0`. Python 3.11 or newer. It depends on Warden for the shapes of a proposal, and on nothing else. It is pinned to Warden tag `v0.11.0`; see "Testing against the pin" below.

## WHAT IT DOES NOT OWN

- Finding problems or counting anything (Ghost Tools). Every number Drafter uses comes from a Ghost finding.
- Writing files, granting permission, running tests, deciding the loop is done (Warden).
- Testing whether the detectors are any good (SWIZZLE).
- The answer key (ASSAY).
- Beautifying the code and writing the final README (Burnish, once, after the loop ends).

## ARCHITECTURAL STORY

```text
Ghost finding  ->  Drafter.propose(target, findings, baseline)  ->  Transformation (data)
                                                                         |
                                                    Warden: grant, suite, apply, re-inspect
```

`Drafter.propose` walks the findings in order. For each one it looks up a fixer by Ghost's detector name. The first fixer that can close its finding safely returns an edit, and Drafter wraps it as a proposal. If no fixer can, it returns `None`, which is how it says it has nothing left. That is not a claim the tree is clean: Ghost may still report findings no fixer here handles.

| module | owns |
|---|---|
| `drafter.seat` | the `Drafter` class Warden calls |
| `drafter.fixers` | the table from Ghost detector name to fixer |
| `drafter.fixers.doc_test_count` | the answer to `doc_test_count_drift` (a stale "N tests passed" claim) |
| `drafter.fixers.dead_code` | the answer to `dead_code` (a function or class nothing uses) |
| `drafter.fixers.list_membership` | the answer to `list_membership_in_loop` (a module-level list scanned on every pass of a loop; its brackets become a set's) |
| `drafter._safe` | path, file-reading and number checks every fixer shares |
| `drafter._pyblock` | the plain-text check that a line range is exactly one definition |

## KEY INTERNAL CONCEPTS

- **One intentional change per proposal.** Several findings mean several turns of the loop.
- **Ghost's facts, not Drafter's.** A fixer takes the claim, the lower bound, the line, the name and the `writable` flag from the finding. It never counts tests or decides what is unused.
- **Safe or silent.** A fixer returns nothing rather than guess. Every refusal also writes a plain-language reason into `Drafter.last_skipped`, a list of `(finding id, reason)` for the latest call. `Drafter.describe_skipped()` returns the same list as readable lines; Warden reads it after every call and prints the lines as `drafter_skipped` in its JSON, so a person can see why a finding was left alone.
- **Finding the file.** The path in a finding is tried as given under the target. Only if no such file exists is a leading folder equal to the target's own name removed (older Ghost output spelled a root-level file as `tgt/m.py`). The file must be a real file inside the target: no `..`, no symlink on the way, not under `tests`, `.git`, `.venv` or `.github`, and not a test file or a test or build configuration file.
- **Checking Ghost's lines.** Before proposing to remove code, Drafter reads the file as plain text (it may not use a Python parser) and requires that Ghost's lines are exactly one `def`, `async def` or `class` at the left edge, running to where Ghost says it ends. Anything odd is refused: a body on the header line, tabs mixed with spaces, a backslash line continuation, a multi-line string with text at the left edge, a second definition of the same name, or the name used as a decorator.
- **Smallest possible document edit.** Only the claim phrase (the number, "tests", and a following "passed", "passing" or "collected") is replaced. The rest of the line is untouched. A leading BOM and the file's line endings are kept.
- **Same input, same answer.** Drafter keeps no memory between calls. It does not loop on its own: once a fix is applied Ghost stops reporting the finding, and Warden also stops if a proposal repeats.
- **No writes.** Drafter never opens a file for writing. A test reads its own source to prove it.
- **Conservative removal.** Ghost's "dead" means no syntax node names the function. Drafter also declines (and records why in `describe_skipped`) when Ghost's `dynamic_lookup_possible` is anything but `no`; when the name appears anywhere in the repository outside its own definition (a string, an attribute, an `__all__`, a `.pyi` stub, a config or docs file, an import or re-export, `TYPE_CHECKING`); when a file in the same package looks things up by a computed name or glues a piece of the name onto a quoted prefix or suffix; when the module is star-imported; when it carries any decorator (a call or attribute form is treated as registering); or when it has a dunder, protocol, abstract, property or overload role. A call inside `try/except` is not evidence of safety.
- **Test-count claims.** Only the project's root README is rewritten, and only when the sentence reads as this project's own suite. Sub-package READMEs, other documents, "upstream has N tests", "added N tests", "before the fix, N tests failed", platform or version phrases, and a count followed by "failed", "skipped" or "errors" are declined.
- **List to set, only when nothing can tell.** For `list_membership_in_loop`, Ghost names the container, says whether the literal is a list or a tuple, and gives the line it is defined on. The fixer reads the file's tokens (the standard library's tokenizer, which builds no syntax tree and decides nothing) and changes the literal's two brackets to braces, nothing else. It refuses unless the literal sits at column 0, is bound exactly once, holds only plain hashable literals (strings that are not f-strings, whole or decimal numbers, `None`, `True`, `False`), is used in the same file only in membership tests (`in`, `not in`; never iterated, indexed, measured, concatenated, called, rebound or exported), and is mentioned in no other file of the repository, not even in a string or a document.
- **Scope.** Every proposal carries `scope_hint` (`"code"` or `"documentation"`), and `Drafter.scope_of(finding)` answers the same from the detector name alone, with no file reads. `Drafter(scope="documentation")` tries in-scope findings first and skips the rest. Warden sets `scope` from the human grant before the first call (Warden 0.11.0 or newer), so under a documentation grant the dead-code fixer is skipped with a reason instead of being proposed and declined.

## IMPORTANT BOUNDARIES

Drafter imports `warden.models` and nothing else from the stack. It does not import Burnish, Ghost Tools, SWIZZLE or ASSAY, and it does not use `ast` or `subprocess`. `tests/test_independence.py` enforces all of that.

## Install

```bash
pip install "git+https://github.com/wking53214/Warden.git@v0.11.0"
pip install git+https://github.com/wking53214/Drafter.git
```

### Bumping the Warden pin

This package depends on one exact Warden commit (see `dependencies` in `pyproject.toml`), so a change on
Warden's `main` cannot break it without anyone noticing. To move to a newer Warden:

1. Pick the Warden commit (or `vX.Y.Z` tag) you want.
2. Put it after the `@` in the `warden @ git+...` line of `pyproject.toml`.
3. Run `pip install -e ".[dev]"` and `pytest`. The tests check that the pin is a tag or a full commit and that
   this package's `requires_contract` matches the installed Warden's `CONTRACT`.
4. Open a pull request. CI runs the same checks.

## Usage

No command line of its own. Warden loads it:

```bash
warden tagteam PATH --drafter drafter.seat:Drafter --authorize ACTOR --reason TEXT --ghost-root GHOST_TOOLS
```

## LIFECYCLE / EXECUTION MODEL

Warden calls `Drafter.propose` once per cycle and stops calling it when it returns `None`.

## WHAT WORKS

- A stale "N tests passed" claim is rewritten to say "at least M `test_*` functions (an earlier version of this document gave N)", using Ghost's M, and nothing else on the line changes. **VERIFIED** by `tests/test_doc_claims.py`.
- The claim is refused (with a reason) inside a link, image, URL, backticks, HTML tag, comment or front matter; inside a code fence or indented code; on a heading (including a setext heading), in a table row; in `CHANGELOG`, `HISTORY`, `NEWS` or `RELEASES` files; when the number looks like part of a version such as 3.10; when the digits are not plain ASCII; and when Ghost's lower bound is not above the claim. **VERIFIED** by the same file.
- Dead code is proposed for removal only when Ghost's lines match the text exactly. The red team's cases (a span that runs into the next function, a span that stops mid-body, a decorator left behind) are all refused or handled. **VERIFIED** by `tests/test_conservative.py` for the round-two repros (computed lookups, re-exports, stubs, `TYPE_CHECKING`, registering decorators). **VERIFIED** by `tests/test_dead_code_spans.py`.
- A root-level file reported as `tgt/m.py` is found. **VERIFIED** by `tests/test_paths.py` and by `tests/test_real_ghost.py`.
- Odd input (a file that is not UTF-8, missing or wrong-typed fields, junk instead of findings, a bad target) gives no proposal and a reason, never a crash. **VERIFIED** by `tests/test_odd_input.py`.
- With the real Ghost scan and the real Warden loop, a root-level module, a nested module, a three-folder-deep module and two README claims (one in the root, one in a subfolder) each produce a proposal that Warden applies cleanly, and the loop then converges. **VERIFIED** by `tests/test_real_ghost.py`.
- A module-level list of ten strings tested with `in` inside a loop becomes a set, byte for byte otherwise (a tuple too; a multi-line literal with comments, CRLF and a BOM all kept); every other kind of element (an f-string, a name, a tuple, a hex number, implicit concatenation) and every other kind of use (iteration, indexing, `len`, concatenation, a method, a rebinding, a keyword argument, a mention in a string, another file or a document) is refused with a reason; an old Ghost that does not name the container gets no proposal; and through the whole gate the set stands and Ghost falls silent. **VERIFIED** by `tests/test_list_membership_fixer.py`.
- Seated in the whole circuit (Ghost, SWIZZLE, ASSAY, Judge and Burnish all live, through `warden tagteam --stack`), a dead function is commented out under a `code` grant and skipped with a reason under a `documentation` grant; both runs end `ACCEPT`, exit 0. **VERIFIED** by hand on 2026-10-14 on a scratch repository; recorded in Warden's `docs/REGISTRY.json`.
- It imports only `warden.models`, never writes, never counts. **VERIFIED** by `tests/test_independence.py`.

304 tests are collected in this tree. With Ghost Tools and Warden on the import path, 304 pass on Warden `v0.11.0` on CPython 3.13 (run 2026-10-14).

Without Ghost Tools on the import path, the 6 tests in `tests/test_real_ghost.py` and the 2 real-Ghost tests in `tests/test_list_membership_fixer.py` skip with the reason "the real Ghost scan needs ghost_buster on PYTHONPATH". Install Ghost Tools (`pip install "git+https://github.com/wking53214/ghost_tools.git@V1.9.1"`) to run them. The 5 full-gate tests in `tests/test_in_the_loop.py` and `tests/test_real_ghost.py` also need SWIZZLE and ASSAY checkouts beside this one (folder names matched without regard to case, or point `CIRCUIT_ROOT` at the folder that holds them) and the Judge importable; otherwise they skip and say so. Nothing else is skipped.

### Testing against the pin

Drafter's tests import Warden from the import path. Against the pinned tag `v0.11.0`, all 304 pass on CPython 3.13 with Ghost Tools, SWIZZLE, ASSAY and the Judge beside this checkout (checked 2026-10-14). `v0.11.0` also sets the Drafter's `scope` from the grant; `v0.10.1` does not, and the tests pass against it too, since none depends on the handoff. `v0.10.1` and `v0.11.0` both carry the held-result rule that `tests/test_real_ghost.py::test_an_unverified_run_puts_the_applied_edit_back` expects; `v0.9.0` does not, so that test fails on the old pin.

## WHAT IS BEAUTIFUL

The fixer's refusals. Every unsafe case returns nothing, so the worst Drafter can do is propose less.

## WHAT IS IMPLEMENTED

Three fixers: `doc_test_count_drift`, `dead_code` and `list_membership_in_loop`.

## WHAT IS PROVEN

The tests named above: against hand-built Ghost findings on scratch trees, and (when Ghost Tools is importable) against the real Ghost scan feeding the real Warden loop on scratch repositories.

## WHAT IS NOT PROVEN

- A run against a large real repository. The end-to-end tests use small scratch repositories, and so does the recorded circuit run.
- That the text-level definition check agrees with a real parser on every possible Python file. It is stricter than Python on purpose and refuses when unsure, and Warden's keep test and comment-out test remain the real gate. But it was written and tested by hand, not checked against a large body of real code.
- Python's newer f-string rules (quotes reused inside braces) can confuse the small scanner. The likely result is a refusal, not a wrong edit, but this is not proven.

## WHAT DOES NOT WORK

- Only three kinds of finding can be fixed. Every other Ghost detector is ignored.
- Only Markdown files are rewritten for claims, and only `.py` files for dead code and list membership.
- The list fixer needs a Ghost that reports `name`, `container` and `defined_at` on the finding (ghost_tools after 1.9.1). An older Ghost's finding gets no proposal and a reason.
- A document claim split across two lines is skipped, as is a claim that is not below Ghost's lower bound (no edit is made when the number is not an undercount).
- Ghost does not report a decorated function as dead (it counts a decorator as a use), so the decorator handling is exercised by hand-built findings only.
- Drafter has no output of its own. The reasons it stayed silent reach a person only through Warden's `drafter_skipped` field (at most 20 lines, each cut to 200 characters).

## WHAT IS STILL UGLY

- The claim wording changes the meaning slightly on purpose: "16 tests passed" becomes "at least 79 `test_*` functions", because Ghost counts test functions and does not run them. Where the claim began a sentence, the sentence starts "The suite holds"; elsewhere it reads "at least M ...". Odd sentences can still read a little stiffly.
- The text scanner and the Markdown checks are hand-rolled, so they are long.

## KNOWN DEFECTS

- A list item or paragraph nested four or more spaces deep is refused as if it were a code block, even when it is a nested list. This costs a missed fix, not a wrong one.
- The list fixer cannot see what is on the left of `in`. Against a list, `x in NAME` is False for an unhashable `x`; against a set it raises `TypeError`. If a caller ever passes a list or a dict there, the fixed code crashes where the old code was silently False, and only a test that exercises that call will catch it. Found by red team on 2026-10-14; left as a limit because refusing it would refuse every fix.
- A line that has a `|` anywhere is treated as a table row and refused.

## WHAT REMAINS OUTSTANDING

More fixers, each added only for a Ghost detector whose finding has a safe mechanical answer. A recorded run on a real repository rather than a scratch one.

## CLAIMS VS REALITY

The README says Drafter never writes and never measures. The tests read its source and fail if it opens a file for writing or imports `ast`. The README does not say it fixes much, because it does not.

## Status

Experimental, version 0.1.0, maintained by one person.

## Support

Open an issue at https://github.com/wking53214/Drafter/issues.

## Contributing

Welcome, narrowly. A new fixer must answer a Ghost detector whose finding has a safe mechanical fix, must return nothing when unsure, and must come with a test that shows both.

## License

Apache-2.0. See `LICENSE`.
