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
| `drafter.fixers.doc_test_count` | the answer to `doc_test_count_drift` |

## KEY INTERNAL CONCEPTS

- **One intentional change per proposal.** Several findings mean several turns of the loop.
- **Ghost's facts, not Drafter's.** A fixer reads the claim, the lower bound, the line and the `writable` flag from the finding. It does not parse the tree.
- **Safe or silent.** A fixer returns nothing rather than guess. A table row, a heading, a file outside the target, or a sentence Ghost marked not writable all produce no proposal.
- **No writes.** Drafter never opens a file for writing. A test reads its own source to prove it.

## IMPORTANT BOUNDARIES

Drafter imports `warden.models` and nothing else from the stack. It does not import Burnish, Ghost Tools, SWIZZLE or ASSAY, and it does not use `ast` or `subprocess`. `tests/test_independence.py` enforces all of that.

## Install

```bash
pip install git+https://github.com/wking53214/Warden.git
pip install git+https://github.com/wking53214/Drafter.git
```

## Usage

No command line of its own. Warden loads it:

```bash
warden tagteam PATH --drafter drafter.seat:Drafter --authorize ACTOR --reason TEXT --ghost-root GHOST_TOOLS
```

## LIFECYCLE / EXECUTION MODEL

Warden calls `Drafter.propose` once per cycle and stops calling it when it returns `None`.

## WHAT WORKS

- A stale "N tests passed" sentence becomes "The suite holds at least M `test_*` functions (an earlier version of this document gave N)", using Ghost's M. **VERIFIED** by `tests/test_fixer.py`.
- List markers survive; tables and headings are left alone; a path outside the target is refused, including `../`. **VERIFIED** by `tests/test_fixer.py`.
- Seated in Warden's loop, it fixes a README and then runs dry, and the loop converges. **VERIFIED** by `tests/test_in_the_loop.py`.
- It imports only `warden.models`, never writes, never counts. **VERIFIED** by `tests/test_independence.py`.

12 tests exist in this tree, and all 12 passed on CPython 3.13 on 2026-10-08.

## WHAT IS BEAUTIFUL

The fixer's refusals. Every unsafe case returns nothing, so the worst Drafter can do is propose less.

## WHAT IS IMPLEMENTED

One fixer, for `doc_test_count_drift`.

## WHAT IS PROVEN

The tests named above, against hand-built Ghost findings and a scratch tree.

## WHAT IS NOT PROVEN

- A run against a live Ghost scan of a real repository.
- That Ghost re-inspection stops reporting the claim after the rewrite, with the real detector rather than the fixture. The wording was chosen so Ghost's claim pattern does not match it; no test has run the real detector on it yet.

## WHAT DOES NOT WORK

- Only one kind of finding can be fixed. Every other Ghost detector is ignored.
- Only Markdown files are handled.

## WHAT IS STILL UGLY

- The sentence rewrite is a regular expression on one line. A claim split across lines is skipped.

## KNOWN DEFECTS

- A claim in a sentence that also carries other facts loses those facts, because the whole sentence is replaced.

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
