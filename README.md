# Drafter

*Formerly Proposer. Renamed in October 2026; the role is unchanged.*

The in-loop maker. It reads what Ghost Tools found and proposes one fix at a time. It never writes a file.

## WHAT THIS IS

One of six repositories in a stack that improves code under human control. Drafter has one job: given a Ghost Tools finding, return the change that would close it, as data. [Warden](https://github.com/wking53214/Warden) runs the loop around it. Warden asks Drafter for a change, checks a person granted it, runs the target's tests, applies the change, runs the tests again, and has Ghost look again. Drafter is then asked again, until it has nothing left to propose.

Version `0.1.0`. Python 3.11 or newer. It depends on Warden for the shapes of a proposal, and on nothing else.

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
| `drafter._safe` | path, file-reading and number checks every fixer shares |
| `drafter._pyblock` | the plain-text check that a line range is exactly one definition |

## KEY INTERNAL CONCEPTS

- **One intentional change per proposal.** Several findings mean several turns of the loop.
- **Ghost's facts, not Drafter's.** A fixer takes the claim, the lower bound, the line, the name and the `writable` flag from the finding. It never counts tests or decides what is unused.
- **Safe or silent.** A fixer returns nothing rather than guess. Every refusal also writes a plain-language reason into `Drafter.last_skipped`, a list of `(finding id, reason)` for the latest call. Warden's Drafter protocol has no channel for notes, so Warden does not print it today. `Drafter.describe_skipped()` returns the same list as readable lines for any caller that wants them.
- **Finding the file.** The path in a finding is tried as given under the target. Only if no such file exists is a leading folder equal to the target's own name removed (older Ghost output spelled a root-level file as `tgt/m.py`). The file must be a real file inside the target: no `..`, no symlink on the way, not under `tests`, `.git`, `.venv` or `.github`, and not a test file or a test or build configuration file.
- **Checking Ghost's lines.** Before proposing to remove code, Drafter reads the file as plain text (it may not use a Python parser) and requires that Ghost's lines are exactly one `def`, `async def` or `class` at the left edge, running to where Ghost says it ends. Decorators directly above are removed with it. Anything odd is refused: a body on the header line, tabs mixed with spaces, a backslash line continuation, a multi-line string with text at the left edge, a second definition of the same name, or the name used as a decorator.
- **Smallest possible document edit.** Only the claim phrase (the number, "tests", and a following "passed", "passing" or "collected") is replaced. The rest of the line is untouched. A leading BOM and the file's line endings are kept.
- **Same input, same answer.** Drafter keeps no memory between calls. It does not loop on its own: once a fix is applied Ghost stops reporting the finding, and Warden also stops if a proposal repeats.
- **No writes.** Drafter never opens a file for writing. A test reads its own source to prove it.

## IMPORTANT BOUNDARIES

Drafter imports `warden.models` and nothing else from the stack. It does not import Burnish, Ghost Tools, SWIZZLE or ASSAY, and it does not use `ast` or `subprocess`. `tests/test_independence.py` enforces all of that.

## Install

```bash
pip install git+https://github.com/wking53214/Warden.git
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
- Dead code is proposed for removal only when Ghost's lines match the text exactly. The red team's cases (a span that runs into the next function, a span that stops mid-body, a decorator left behind) are all refused or handled. **VERIFIED** by `tests/test_dead_code_spans.py`.
- A root-level file reported as `tgt/m.py` is found. **VERIFIED** by `tests/test_paths.py` and by `tests/test_real_ghost.py`.
- Odd input (a file that is not UTF-8, missing or wrong-typed fields, junk instead of findings, a bad target) gives no proposal and a reason, never a crash. **VERIFIED** by `tests/test_odd_input.py`.
- With the real Ghost scan and the real Warden loop, a root-level module, a nested module, a three-folder-deep module and two README claims (one in the root, one in a subfolder) each produce a proposal that Warden applies cleanly, and the loop then converges. **VERIFIED** by `tests/test_real_ghost.py`.
- It imports only `warden.models`, never writes, never counts. **VERIFIED** by `tests/test_independence.py`.

225 tests exist in this tree. All 225 passed on CPython 3.13 on 2026-10-09 with the real Ghost Tools and Warden on the path. Without Ghost Tools importable, 220 run and the 5 end-to-end tests skip with a stated reason.

## WHAT IS BEAUTIFUL

The fixer's refusals. Every unsafe case returns nothing, so the worst Drafter can do is propose less.

## WHAT IS IMPLEMENTED

Two fixers: `doc_test_count_drift` and `dead_code`.

## WHAT IS PROVEN

The tests named above: against hand-built Ghost findings on scratch trees, and (when Ghost Tools is importable) against the real Ghost scan feeding the real Warden loop on scratch repositories.

## WHAT IS NOT PROVEN

- A run against a large real repository. The end-to-end tests use small scratch repositories.
- The full chain with SWIZZLE, ASSAY and the Judge seated. The loop was run with Ghost, Warden and Drafter only.
- That the text-level definition check agrees with a real parser on every possible Python file. It is stricter than Python on purpose and refuses when unsure, and Warden's keep test and comment-out test remain the real gate. But it was written and tested by hand, not checked against a large body of real code.
- Python's newer f-string rules (quotes reused inside braces) can confuse the small scanner. The likely result is a refusal, not a wrong edit, but this is not proven.

## WHAT DOES NOT WORK

- Only two kinds of finding can be fixed. Every other Ghost detector is ignored.
- Only Markdown files are rewritten for claims, and only `.py` files for dead code.
- A document claim split across two lines is skipped, as is a claim that is not below Ghost's lower bound (no edit is made when the number is not an undercount).
- Ghost does not report a decorated function as dead (it counts a decorator as a use), so the decorator handling is exercised by hand-built findings only.
- Warden's protocol gives Drafter no way to tell the user why it stayed silent. The reasons are in `Drafter.last_skipped` but nothing prints them yet.

## WHAT IS STILL UGLY

- The claim wording changes the meaning slightly on purpose: "16 tests passed" becomes "at least 79 `test_*` functions", because Ghost counts test functions and does not run them. Where the claim began a sentence, the sentence starts "The suite holds"; elsewhere it reads "at least M ...". Odd sentences can still read a little stiffly.
- The text scanner and the Markdown checks are hand-rolled, so they are long.

## KNOWN DEFECTS

- A list item or paragraph nested four or more spaces deep is refused as if it were a code block, even when it is a nested list. This costs a missed fix, not a wrong one.
- A line that has a `|` anywhere is treated as a table row and refused.

## WHAT REMAINS OUTSTANDING

More fixers, each added only for a Ghost detector whose finding has a safe mechanical answer. A live run seated in Warden's loop, recorded.

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
