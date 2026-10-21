# Changelog

All notable changes to Drafter. The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and the version follows [Semantic Versioning](https://semver.org/). An older tag, `v0.10.0`, exists in this
repository from earlier numbering (it points at a commit whose `pyproject.toml` says 0.1.0) and does not correspond
to any version below. Releases of these versions are not tagged yet; tagging is the owner's decision. The versions
below are the ones `pyproject.toml` declared.

## [0.2.7] - 2026-10-21

### Changed

- CNS is pinned by its release tag, `cns @ git+https://github.com/wking53214/CNS.git@v1.9.0` (the tag peels to
  `da18e411743d4e3b0e783105394d845fb1c16746`), replacing the full-commit spelling, so the pin text matches Warden's own
  CNS pin and the other repositories of the circuit (pip treats a tag URL and a commit URL as two sources).
  `test_the_cns_dependency_is_pinned_to_a_full_commit` asserted the old spelling and now asserts the tag spelling.
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
