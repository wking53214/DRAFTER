# Changelog

All notable changes to Drafter. The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and the version follows [Semantic Versioning](https://semver.org/). An older tag, `v0.10.0`, exists in this
repository from earlier numbering (it points at a commit whose `pyproject.toml` says 0.1.0) and does not correspond
to any version below. Releases of these versions are not tagged yet; tagging is the owner's decision. The versions
below are the ones `pyproject.toml` declared.

## [0.2.16] - 2026-10-30, not tagged

### Changed

- Stage 3 wave 2 step 1: the Warden pin moves from 0.16.1 (`fade3ca5ee6435393d0588782929ff8de72f988f`) to 0.16.2
  (`df212db32c230a00cf4100038637be873262a816`), which refuses a `--stack` folder that holds a seat the pinned manifest omits
  even when `--claim-commit`, `--claim-diff`, `--drafter` or `--finisher` supplies the seat. The README sentence that names
  the pinned Warden release follows. No Drafter code changed. The CI tested set is not moved. No test was edited.
- Stage 3 wave 2 step 2: version 0.2.16 (`drafter/__init__.py`, `pyproject.toml`, README version line) and this entry.

## [0.2.15] - 2026-10-30, not tagged

### Changed

- Pin22 step 1: the CNS pin is the tag `v2.2.0` (`cns @ git+https://github.com/wking53214/CNS.git@v2.2.0`, comment
  `v2.2.0 = ce6bd05578a7a3e3cafa0cfa1e9a2cca8a5f171f`, a lightweight tag), from `v2.1.0`. The `cns` package at v2.2.0
  equals v2.1.0 except its version string. The Warden pin moves from 0.15.1 (`fe9c8b35778de680d04b2a57775ac6a6831f4799`)
  to 0.16.1 (`fade3ca5ee6435393d0588782929ff8de72f988f`). No Drafter code changed. The README CNS note and the Warden
  release it names follow the pins. The CI tested set is not moved. No test was edited.
- Pin22 step 2: version 0.2.15 (`drafter/__init__.py`, `pyproject.toml`, README version line) and this entry.
- Runs that seat this Drafter under Warden now carry eight declined checks (`mutate`, `kernel`, `structure`, `tests`,
  `project`, `secrets`, `correlate`, `ledger`), not seven, because ghost_tools 1.10.11 lists the ledger as declined under
  `--no-ledger`. Drafter states no such count in its text and its code is unchanged.

## [0.2.14] - 2026-10-29, not tagged

### Changed

- Pin21 step 1: the CNS pin is the tag `v2.1.0` (`cns @ git+https://github.com/wking53214/CNS.git@v2.1.0`, comment
  `v2.1.0 = fde931ffa89aebec95647742256ad53033bd3d02`), from `v2.0.0`, and the Warden pin moves from 0.14.0
  (`68f2a955f486a8ebb230c4395c88f7e99ee47c48`) to 0.15.1 (`fe9c8b35778de680d04b2a57775ac6a6831f4799`). No Drafter code
  changed. The README CNS note and the Warden release it names follow the pins. The CI tested set is not moved. No
  test was edited.
- Pin21 step 2: version 0.2.14 (`drafter/__init__.py`, `pyproject.toml`, README version line) and this entry.

## [0.2.13] - 2026-10-29, not tagged

### Changed

- Step R1: the README says, in WHAT THIS IS and in CEILINGS CODE CANNOT FIX, that the owner released the Drafter repository
  from its role as a required seat in the Horsemen circuit on 2026-10-29. Released means removed from the circuit and nothing
  else: no code, test, history or CI was changed. Drafter still works on its own (its fixers, the `Drafter` class when a
  caller seats it, and the `drafter propose` dry run). The seat interface stays and Warden's claim seat fills it for a real
  change. Warden 0.15.0 lets a pinned manifest leave Drafter out; until the pins move, the circuit still installs it. Drafter
  is free to be reborn elsewhere, as intent only.
- Version 0.2.13 and this entry. No pin changed.

## [0.2.12] - 2026-10-24

Wave F: the fixes the round-6 independent audit of the final release set asked for. Each item was reproduced before it
was changed.

### Changed

- Step 1: the guard `test_the_drafter_never_opens_a_file_for_writing` is no longer a substring search. It reads the
  syntax tree of every module and fails on any call that opens a file for writing or changes the filesystem (`open`,
  `io.open`, `io.FileIO`, `Path.open`, `os.open`, aliased imports, a mode it cannot read, `write_text`, `os.replace`,
  `shutil`, `tempfile`, `eval`, `exec`), with one site named in an exact allowlist: `_silence_stdout` in
  `drafter/cli.py`, which opens the null device on an error path. A second test shows the checker flags each spelling
  and does not flag plain reads. The README and `STACK.md` no longer say "never opens a file for writing" or "never
  writes"; they say that no file of the user's is written and that one error path opens the null device.
- Step 2: `setup.py`, `MANIFEST.in` and `requirements*.txt` are never edited. Reproduced first: a `dead_code` finding in
  `setup.py` got a proposal. The README lists the blocked names; only `.py` and Markdown files are rewritten by the
  current fixers, so the non-Python names are blocked as a precaution.
- Step 3: a dead-code finding with no `dynamic_lookup_possible` key declines, as a missing `framework_hook` already
  did (it used to count as "no"). The README says so.
- Step 4: a malformed record is skipped under its own `id` when that is readable, not under `?`.
- Step 5: the Warden pin moves from `b57b81e1c98333c43d422666c89a8fcf3ae6eaca` (0.13.9) to the full commit
  `9ecd1124e6c1b1c4ad7daed37b17f9009662dd9d` (Warden 0.13.10); CNS stays `@v2.0.0`. The four `integration` sibling pins
  (ghost_tools `5a9154d`, JUDGE `c3001b8`, SWIZZLE `3f35dad`, ASSAY `184679c`) are not moved; the workflow comment and
  the README now call them the last set this repository's CI tested on its own, not the head of any `main`. The README
  loses its repeated sentences, its SELF-HOSTING section cites the CNS repository's
  `docs/evidence/SELFHOSTING_2026-10-23.md` and says what it recorded and does not mean, a known defect is added (the
  stack install alone leaves this repository's suite red), and the ledger gets an entry for each fix above.

### Tests

- Step 1: `tests/test_independence.py` gains `test_the_write_checker_sees_every_spelling_it_is_meant_to`;
  `test_the_drafter_never_opens_a_file_for_writing` keeps its name and now uses the syntax-tree checker.
- Step 2: `tests/test_paths.py` gains `test_a_dead_code_finding_in_a_build_script_gets_no_proposal` (failed on 0.2.11 for
  `setup.py`), `test_every_build_and_test_configuration_name_is_blocked` and
  `test_a_name_that_only_looks_like_a_build_file_is_still_editable`.
- Step 3: `tests/test_conservative.py` gains the missing-key test (failed on 0.2.11) and its counterpart with the key set
  to `no`. Edited under the rule that a test asserting changed behaviour may be updated, and nothing more: the two helpers
  that build hand-made `dead_code` findings (`tests/support.py` `dead_finding`, `tests/test_dead_code_fixer.py`
  `_finding`) now carry `dynamic_lookup_possible: "no"`, as real Ghost does for a repository with a project root.
  Without it every test built from them would have tested the missing-key case.
  The real-Ghost tests found the same thing from the other side: `tests/test_real_ghost.py` built its scratch target with
  no project file, and real Ghost then leaves `dynamic_lookup_possible` out, so the three `dead_code` cases there got no
  proposal. `_build_code` now writes a `pyproject.toml` into the target, as any real project has (edited in the Step 5
  commit, caused by Step 3, found when the full suite ran). A new test in the same file records the other side: real Ghost
  on a tree with no project root omits the key and the Drafter declines with the reason.
- Step 4: `tests/test_odd_input.py` and `tests/test_cli.py` gain tests that a malformed record keeps its id (failed on
  0.2.11) and that an unreadable id still files under `?`.
- Step 5: `tests/test_readme_ledger.py` holds the self-hosting numbers to constants that name the evidence file, and holds
  the tested-set wording. Edited, with the reason: `tests/test_release.py`
  `test_the_readme_does_not_restate_the_pinned_versions` asserted that the strings `0.11.5`, `v0.11` and
  `pinned to Warden tag` were absent from the README and `pyproject.toml`, a guard from an older era that could not fail;
  it now asserts that the pin comment names exactly one Warden release. The no-full-commit-in-the-README assertion is
  unchanged.

## [0.2.11] - 2026-10-22

### Changed

- The `integration` job's JUDGE checkout moves from `e5c3f98f0f3998a8c5dac458ad0fcf4e050eb074` (0.4.8) to
  `c3001b86764c8946dbc3d367c977aed53cbab9b7` (0.4.10), the head of the JUDGE branch
  `claude/horsemen-production-status-5wsndb`. The workflow comments that said JUDGE was not moved in the 0.2.10
  re-pin are updated to match. Nothing else changed.
- No pre-existing test was edited.

## [0.2.10] - 2026-10-22

### Changed

- CNS is re-pinned from the tag `v1.9.0` to the tag `v2.0.0`: `cns @ git+https://github.com/wking53214/CNS.git@v2.0.0`
  with the comment `# v2.0.0 = b13e5d2f9e0e4291725f82794b89117c3d840ac1`, the same text as every other repository of
  the circuit. Drafter imports only `cns.defect` and `cns.seat`; its suite passes against the installed CNS 2.0.0
  (pip's `direct_url.json` records `requested_revision` `v2.0.0` and the commit above).
- Warden is re-pinned from `380894f0304ef40587dd29efd41b4ceccf94a5d3` (0.13.8) to the full commit
  `b57b81e1c98333c43d422666c89a8fcf3ae6eaca` (Warden 0.13.9). That Warden requires CNS `v2.0.0`, so
  `pip install -e ".[dev]"` resolves and `pip check` is clean. The `Warden.git` spelling is unchanged.
- The `integration` job's sibling checkouts move to the heads of the sibling branches
  `claude/horsemen-production-status-5wsndb`: ghost_tools `5a9154d3c76670f5bf1f46d845acadfed46d7bc8` (1.10.8, was
  `2d03d8e`, 1.10.6), SWIZZLE `3f35dad5568b590c2ee36e60533d50a35db94aa2` (0.8.7, was `5226584`, 0.8.5) and ASSAY
  `184679c06e0a636a9a08a8403efa410b375c9429` (0.11.5, was `a1732f2`, 0.11.3). JUDGE stays at `e5c3f98` (0.4.8). The
  comments beside the refs said "head of ... main", which stopped being true; they now name the package version only,
  and the paragraph above them no longer says the commits are the heads of `main` or that none carries a release tag.
- The README is rewritten: what this is, how to install and run (the commands were run in a fresh virtual environment),
  what works and the test or CI job that shows it, what does not work or is not proven, the open defects, what broke
  and how it was fixed (checked against this file, the git history and the tests), the self-hosting record and the
  ceilings code cannot fix. The "what is beautiful" section is gone (it claimed that the worst Drafter can do is
  propose less, which the known defects below it contradict). The Status paragraph is gone with its statement about
  tags. The Warden release the README names is now 0.13.9. The preamble of this file still carries its older
  sentences about tags and is left as written.

### Fixed

- `STACK.md` called CNS private. It is a public repository.

### Tests

- Added `tests/test_readme_ledger.py`: the required README sections exist once and in order, every test the README
  names exists, every version and date in the ledger matches a heading in this file, the CI jobs the README names are
  in the workflow, the Warden release the README names equals the one in the pin comment, no marketing words, no
  em dashes, no statement about whether release tags exist, and `STACK.md` does not call CNS private.
- No pre-existing test was edited.
- Checked on Python 3.11, 3.12 and 3.13 with the real circuit (ghost_tools, JUDGE, SWIZZLE and ASSAY on the path,
  numpy and matplotlib installed as the `integration` job does): the whole suite passes with no skips; `ruff check .`,
  `mypy` and `pip check` are clean.

## [0.2.9] - 2026-10-22

### Changed

- Warden is re-pinned from `1636e1a21f124eedbf6e158db95dc75344f4308d` (0.13.7) to the full commit
  `380894f0304ef40587dd29efd41b4ceccf94a5d3` (Warden 0.13.8; untagged). The README sentence naming the pinned Warden
  says 0.13.8. The `Warden.git` spelling and the CNS tag pin `@v1.9.0` are unchanged.
- The `integration` job's sibling checkouts move to the heads of the sibling `main` branches, which are also the
  commits the CNS stack manifest records: ghost_tools `2d03d8e19dc5937a6f45379c429d1a3afce4ab29` (1.10.6, was
  `c2ada82`, 1.10.5), SWIZZLE `522658415b026ac3211d3fc130ba7da7c77cc400` (0.8.5, was `6bd88f3`, 0.8.4), JUDGE
  `e5c3f98f0f3998a8c5dac458ad0fcf4e050eb074` (0.4.8, was `cf71fb4`, 0.4.7), ASSAY
  `a1732f2bf3748235661f65b96e590a6d44ace71c` (0.11.3, was `54248be`, 0.11.2). The version note beside each ref says
  the same.

### Fixed

- A report that cannot be written to stdout no longer ends as a traceback with exit 1. With stdout on a full device,
  `drafter propose T --findings F` ended in `OSError: [Errno 28]` from the print, and with file descriptor 1 closed in
  `AttributeError: 'NoneType' object has no attribute 'flush'` from the flush; both exited 1, which the exit-code table
  defines as "nothing to propose", so they read as a clean no-op. Only `BrokenPipeError` was handled (exit 4). Now any
  `OSError` from the print or flush, and the `AttributeError` of a closed stdout, write one plain line to stderr and
  exit 4, the existing "report not delivered" code. A closed stdout used to raise the same `AttributeError` after an
  exit 2 or exit 3 as well; the flush now sits inside the guarded block, so those codes are reported as they are.
- The 0.2.8 entry says the exit-code table "stays true". It did not cover this case: exit 4 is now also the answer when
  stdout is full or closed, and the README row for exit 4 and the module docstring say so. The table still has the same
  five codes; row 4 was widened rather than a sixth row added, since the code is the existing one. The 0.2.8 entry is
  left as written.
- `drafter propose ""` silently made the current directory the target (`Path("")` is the current folder). An empty
  PATH is now a usage error: one plain line on stderr and exit 2. The README row for exit 2 and the module docstring
  name it.

### Tests

- Added tests that fail on the 0.2.8 code (`tests/test_cli.py`): a full-device stdout and a `None` stdout in process;
  the real thing in a subprocess with `stdout=open('/dev/full', 'wb')` and with file descriptor 1 closed; an empty PATH
  in process and as a subprocess; and the README exit 2 and exit 4 rows.
- No pre-existing test was edited.

## [0.2.8] - 2026-10-21

### Changed

- Warden is re-pinned from `0c1ea567f0b69586cfd735f82260774aec9552bb` (0.13.6) to the full commit
  `1636e1a21f124eedbf6e158db95dc75344f4308d` (Warden 0.13.7; untagged). The README sentence naming the pinned Warden
  says 0.13.7. The `Warden.git` spelling and the CNS tag pin `@v1.9.0` are unchanged.
- The `integration` job's sibling checkouts move to the heads of the sibling `main` branches, which are also the
  commits the CNS stack manifest records: ghost_tools `c2ada82d2f6c0404074a668ba749c7872743aad9` (1.10.5, was
  `aa72c38`, 1.10.3), SWIZZLE `6bd88f3a6e9de1f83e64f401e13cbcb5233499fc` (0.8.4, was `ec7543c`, 0.8.2), JUDGE
  `cf71fb468d483e868834c8c06b650a5d60726967` (0.4.7, was `1e77209`, 0.4.5). ASSAY stays at `54248beb` (0.11.2). The
  comments beside the refs and above them say what the pins are. The earlier entries below name the sets that were
  current at the time and are left as written; the 0.2.5 line that calls JUDGE `f26db68` "the head of its branch,
  which the stack manifest set moves to" described that day only.
- README Install: the CNS install file is on CNS `main`, so the instruction to use a CNS branch "until that is on
  `main`" is gone, and the sentence that said this repository's `main` "still holds the 0.1.0 code" (no longer true:
  `main` has the command line) is replaced by what is true: `main` moves and nothing there says it was tested with
  the other repositories.

### Fixed

- A findings record that names no usable `detector` (missing, empty, null or not text) is now listed in `skipped`
  with the reason "the finding names no detector (it is missing, empty or not text), so Drafter cannot tell what kind
  of finding it is". Before, `drafter propose PATH --findings F` with `[{"id":"x"}]` printed `findings: 1`,
  `proposal: null`, `skipped: []` and exited 1, so the report could not say why. A finding for a detector Drafter has
  no fixer for is still not listed (that is not its business). The same reason reaches Warden's `drafter_skipped`.
- A record whose fields have the wrong type (for example `evidence` that is not an object, or `attributes` that is
  not a mapping) made Warden's reader raise inside `drafter propose`; the traceback escaped with exit 1, which reads
  as "nothing to propose". The record is now passed to the Drafter as it is, which lists it as "a finding could not
  be read (...)", and the records after it are still read.
- The exit-code table in the README is unchanged and stays true: a malformed record exits 1 and the JSON lists why
  (row 1 already says "the JSON still lists why findings were skipped"); exit 3 stays for findings that cannot be
  obtained at all. A test holds the table to that wording.
- Text only: the 0.2.7 entry cited `test_the_cns_dependency_is_pinned_to_a_full_commit` as if it were current; it now
  says that test was renamed `test_the_cns_dependency_is_pinned_to_its_release_tag`.

### Tests

- Added tests for both malformed-record cases (`tests/test_cli.py`, `tests/test_odd_input.py`).
- Edited under the repository rule that a test asserting a changed behaviour may be updated: only a rename.
  `test_cns_is_pinned_to_the_same_commit_as_wardens_own_cns_pin` is now
  `test_the_cns_pin_text_equals_wardens_own_cns_requirement`, with a docstring that says it compares pin text (a
  tag). Its assertion is unchanged. Caused by the README and test slips step.

## [0.2.7] - 2026-10-21

### Changed

- CNS is pinned by its release tag, `cns @ git+https://github.com/wking53214/CNS.git@v1.9.0` (the tag peels to
  `da18e411743d4e3b0e783105394d845fb1c16746`), replacing the full-commit spelling, so the pin text matches Warden's own
  CNS pin and the other repositories of the circuit (pip treats a tag URL and a commit URL as two sources).
  The test that asserted the old spelling, formerly `test_the_cns_dependency_is_pinned_to_a_full_commit`, is now
  `test_the_cns_dependency_is_pinned_to_its_release_tag` and asserts the tag spelling.
- Warden is re-pinned from `decc3c3b5af479ad0eef3df4d66dbcb21e90897c` (0.13.5) to the full commit
  `0c1ea567f0b69586cfd735f82260774aec9552bb` (Warden 0.13.6; untagged). The README sentence naming the pinned Warden
  says 0.13.6.
- The `integration` job's ASSAY checkout is `54248beb5a36600f69de7c816cb2271dda20a879` (0.11.2, the head of its
  `main`), replacing `01c713a316dc0513d30e566fffe4d94536888e81`.

## [0.2.6] - 2026-10-21

### Changed

- Merged `origin/main` (`41ec214`, pull request #13) into this branch with a merge commit. Its two changed files,
  `README.md` and `pyproject.toml`, conflicted; both were resolved by keeping this branch's side (the install-file
  instructions, the full-commit pins with tag comments, the Python 3.13 classifier), so main's Warden `72e5745` and
  CNS tag spellings are superseded by the pins below.
- CNS is re-pinned from `5252ceebe98185f7be81212d988055ccf9884568` (v1.8.0) to the full commit
  `da18e411743d4e3b0e783105394d845fb1c16746` (v1.9.0). It stays a full commit, not the tag, because pip treats a tag URL
  and a commit URL as two sources.
- Warden is re-pinned from `36e98433f4928b7d12905f02b56e55ee1943b56e` (0.13.4) to the full commit
  `decc3c3b5af479ad0eef3df4d66dbcb21e90897c` (Warden 0.13.5; untagged). That Warden requires the same CNS commit.
- The `integration` job's sibling checkouts: ASSAY `01c713a316dc0513d30e566fffe4d94536888e81` (0.11.2, the head of its
  `main`), JUDGE `1e77209e8a64edf95f2a1b50195526fa37c9e5de` (0.4.5), ghost_tools
  `aa72c38294acac1da4c32a2752f0db58e2b07248` (1.10.3) and SWIZZLE `ec7543cb10f9b78926e38e819c906721520dc052` (0.8.2).
  Only the ASSAY ref changed in this re-pin; it replaces `b6b1ccf`, which is not the head of ASSAY `main`.

### Fixed

- Text only: the README said Warden 0.13.3 refuses a Ghost scan with no named root. That refusal first appears in Warden
  0.13.2, so the README, the `drafter/cli.py` docstring and one test docstring now say "0.13.2 and later". The README
  also says the git-checkout and site-packages requirement is Warden 0.13.4 and later, and that the pin is 0.13.5.

## [0.2.5] - 2026-10-21

### Changed

- Warden is re-pinned from `580f659` (0.13.3) to the full commit `36e98433f4928b7d12905f02b56e55ee1943b56e`
  (Warden 0.13.4; untagged). Warden 0.13.4 requires an instrument root to be a git checkout with a readable version
  and refuses a site-packages root. Drafter's integration tests and CI use clean clones, so no test or assertion
  changed. The pin comment says so, and `tests/test_warden_pin.py` checks it against the installed release.
  `pip install -e ".[dev]"` resolves and `pip check` is clean, with no `--no-deps` step.
- The `integration` job's JUDGE checkout moved from `50f90f4` (0.4.3) to `f26db68d960b091c56396d1917ded8785b7af910`
  (0.4.4), the head of its branch, which the stack manifest set moves to. ghost_tools `5d7a386` (1.10.1), SWIZZLE
  `8166c47` (0.8.1) and ASSAY `4c41556` (0.11.1) are unchanged.

## [0.2.4] - 2026-10-21

### Changed

- Warden is re-pinned from `9d9a71d` (0.13.2) to the full commit `580f659336818b4a5a2c0ca235d2344012536426`
  (Warden 0.13.3; untagged). The pin comment says so, and `tests/test_warden_pin.py` checks it against the installed
  release. `pip install -e ".[dev]"` resolves and `pip check` is clean, with no `--no-deps` step.
- The `integration` job's sibling checkouts moved to the commits the CNS stack manifest records (the 0.2.3 entry
  called its set the newest, but it was one commit behind for three of the four): ghost_tools `5d7a386` (1.10.1,
  unchanged), JUDGE `50f90f4` (0.4.3), SWIZZLE `8166c47` (0.8.1), ASSAY `4c41556` (0.11.1). Each comment states the
  package version that was checked.

### Fixed

- The `integration` job failed on Python 3.11: it installed `numpy==2.5.4` on every leg of its matrix, and numpy 2.5
  requires Python 3.12 or newer (on 3.11 pip offers versions only up to 2.4.6), so that leg could not install it and
  the circuit tests could not grade ASSAY's answer key. The install is now pinned per interpreter with environment
  markers: `numpy==2.4.6` below Python 3.12, `numpy==2.5.4` from 3.12, and `matplotlib==3.11.2` on all three. A test
  checks that every numpy pin in the workflow is covered by a marker for every Python in the matrix.
- The README Install section pinned `189d3bd` and called it the commit the circuit's tested set records; the CNS stack
  manifest records a different commit, and a commit cannot name itself. It now says to install with the CNS install
  file (`pip install -r contracts/install-stack.txt` from the CNS repository, on the branch
  `claude/horsemen-production-status-5wsndb` until it is on `main`) or, once a release tag exists,
  `git+https://github.com/wking53214/DRAFTER.git@<tag>`, and names no commit of this repository.
- `drafter propose ... | head` died with a `BrokenPipeError` traceback and exit 1, which reads as "nothing to
  propose". A closed output pipe now prints one line on stderr and exits 4, a code nothing else uses; the README and
  the command's help document it.
- The argparse parsers accept no abbreviated options (`allow_abbrev=False`): `--finding` is a usage error (exit 2)
  instead of silently meaning `--findings`.
- The 0.2.3 entry below said the job installs `numpy==2.5.4`; that was true only for Python 3.12 and 3.13.

## [0.2.3] - 2026-10-21

### Changed

- Warden is re-pinned from `ec551d8` (0.13.1) to the full commit `9d9a71d1bc3195f0abd9aee8fe553cc09838b684`
  (Warden 0.13.2; untagged). The pin comment says so, and `tests/test_warden_pin.py` checks it against the installed
  release. `pip install -e ".[dev]"` resolves and `pip check` is clean, with no `--no-deps` step.
- The `integration` job's sibling checkouts moved to a tested set: ghost_tools `5d7a386` (1.10.1), JUDGE
  `51a58c0` (0.4.2), SWIZZLE `123d7ab` (0.8.1), ASSAY `7b781cf` (0.11.1). Each comment states the package version
  that was checked.

### Fixed

- Warden 0.13.2 refuses a Ghost scan with no instrument root and never lets an installed Ghost Tools stand in for
  one. `drafter propose PATH` with neither `--findings` nor `--ghost-root` therefore exits 3 (findings could not be
  obtained), where its help, module docstring and README still described a default scan. Those texts now say that a
  named root is needed. New tests cover the no-root refusal and a root that does not hold the package; both end in
  exit 3, never exit 1.
- The `integration` job now installs `numpy==2.5.4` and `matplotlib==3.11.2`. ASSAY 0.11.1 exits 1 on a skipped
  claim, and its answer key needs both; Warden's CI installs the same two versions.

## [0.2.2] - 2026-10-17

### Fixed

- The `integration` job pinned JUDGE to `97904c2` (0.4.0) while its comment and the tested set say 0.4.1. It now
  checks out the tested set exactly: ghost_tools `288cefa` (1.10.0), JUDGE `9d8f70e` (0.4.1), SWIZZLE `04b72b1`
  (0.8.0), ASSAY `5aafbf3` (0.11.0). The comments beside the pins state only what was checked (the package
  version, and that the commit is a tested-set pin).
- The README install line installed `main` (0.1.0, which has no command line). It now installs a pinned commit of
  this branch and says to point at a release once one is tagged.
- The README and this file said no tag existed. A `v0.10.0` tag does exist (an earlier numbering, on a 0.1.0
  commit); both now say so and that tagging this version is the owner's decision. No tag was created or moved.

### Changed

- Every GitHub Action in the workflow is pinned to a full commit with its tag in a comment: `actions/checkout`
  v4.2.2 and `actions/setup-python` v5.6.0.
- `tests/test_release.py`: the check that the README restates no full commit now ignores the one install line,
  which is itself checked to be a full-commit pin of this repository. A new test requires every `uses:` in the
  workflow to be a full-commit pin.

## [0.2.1] - 2026-10-17

### Changed

- Warden is re-pinned from `2cf0eec` (0.12.0 line) to the full commit `ec551d8e10f82b6e3e681593a97011ae517d360b`
  (Warden 0.13.1). That Warden pins CNS by the same commit Drafter does, so `pip install -e ".[dev]"` resolves
  cleanly in a fresh environment and `pip check` is clean, with no `--no-deps` step.
- The `integration` job's sibling checkouts moved to the fixed siblings: ghost_tools `288cefa` (1.10.0), JUDGE
  `97904c2` (0.4.0), SWIZZLE `04b72b1` (0.8.0), ASSAY `5aafbf3` (0.11.0). Each carries a bump comment.

### Added

- Tests that the comment beside the Warden pin names the installed Warden release, and that Drafter's CNS pin is
  the same commit as the CNS pin Warden requires.

## [0.2.0] - 2026-10-17

### Added

- `drafter --version` and `drafter propose PATH`, a read-only dry run that prints the proposed edits (and the
  reasons findings were skipped) as JSON. Exit codes: 0 proposal, 1 nothing to propose, 2 usage error, 3 findings
  could not be obtained. `python -m drafter` is the same command.
- Logging through the standard library: the `drafter` logger. A deliberate refusal is DEBUG; a surprise is WARNING
  with its traceback at DEBUG. The library never configures logging; the command line does (`-v`, `-vv`).
- An allowlist-based import test (`tests/test_independence.py`), and tests that an injected bug is observable
  (`tests/test_observable_failures.py`), that the version agrees everywhere (`tests/test_release.py`) and that the
  command line behaves as documented (`tests/test_cli.py`).
- CI: an `integration` job that checks out ghost_tools, JUDGE, SWIZZLE and ASSAY at full commits and runs the
  whole suite with zero skips allowed; a `static` job running ruff and mypy; Python 3.13 in the matrix.
- Ruff (E, F, W, B, BLE, RUF100) and strict mypy configuration in `pyproject.toml`.

### Changed

- A fixer that fails for a reason other than a deliberate refusal now records `internal error (Type: message)`
  as its reason, which Warden prints as `drafter_skipped`, instead of the old "unexpected Type ... left alone".
  The two silent paths (reading a finding, building the proposal) no longer swallow every exception: a
  malformed finding, a Warden mismatch and an unknown failure are told apart. An exception of an unknown type
  while building the proposal now propagates to Warden instead of becoming a quiet "no proposal".
- CNS is pinned to the full commit of its v1.8.0 release instead of the tag name.
- The README no longer restates the Warden pin (it said a tag the code had long left); `pyproject.toml` is the
  one place the pin is written. Test totals were removed from the README, since they went stale.
- The README's claim about imports now names every module the code imports, and a test keeps it true.

### Fixed

- 27 mypy errors in six files (optional values used without a check, a refusal helper not marked as
  never returning, a path type that was too narrow).
- Two `noqa` comments that suppressed nothing, and a lint rule (`zip` without `strict=`).
- `Programming Language :: Python :: 3.13` classifier added; the code already ran on 3.13.

## [0.1.0] - 2026-10-16

The version `pyproject.toml` declared from the first commit until 0.2.0. History, from the git log:

### Added

- 2026-10-08: first release as Proposer, renamed to Drafter the same day: turns a Ghost Tools
  `doc_test_count_drift` finding into a proposed README edit, as data. Added the `dead_code` fixer.
- 2026-10-09: `requires_contract = "1"` on the seat; Warden pinned to a commit. Red-team fixes: root-level paths
  (`tgt/m.py`), span checks, minimal document edits, odd input never crashes.
- 2026-10-10: conservative dead-code removal and test-count edits; `scope_hint` on every proposal.
- 2026-10-12: tests prove the real full-gate ACCEPT; README claims corrected to the test results.
- 2026-10-14: the `list_membership_in_loop` fixer (a module-level list becomes a set); red-team round (a chained
  comparison is refused, the unhashable-operand limit is documented); sibling checkouts found case-blind.
- 2026-10-15: a file with an invalid token is refused on every Python, not only 3.12 and newer; the shared rows
  come from CNS 1.7.0.

### Changed

- Warden pin moved from tag to tag (v0.8.0, v0.9.0, v0.10.0, v0.10.1, v0.11.0, v0.11.3), then to commits
  (0.11.4, 0.11.5) and on 2026-10-17 to the 0.12.0 commit; CNS moved to v1.8.0 on 2026-10-16.
