"""The `drafter` command: a read-only dry run of what the Drafter would propose.

Warden is what runs the Drafter in a loop and applies its proposals. This command
is for a person who wants to see, without writing anything, what the Drafter
would propose for a folder and why it left other findings alone.

    drafter --version
    drafter propose PATH [--findings FILE | --ghost-root DIR] [--scope code|documentation] [-v]

EXIT CODES
    0  a proposal was made (printed as JSON on stdout)
    1  nothing to propose (the JSON still lists why findings were skipped)
    2  usage error: unknown option, or PATH is not a folder
    3  findings could not be obtained: Ghost Tools could not run, or the findings
       file is unreadable. This is "unknown", never "nothing to propose".

Nothing is written. Findings come from a saved Ghost JSON (`--findings`) or from
Warden's own read-only Ghost scan, which needs `--ghost-root` (Warden 0.13.2 refuses a scan with no root, and an
installed Ghost Tools never stands in for one: exit 3).
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path
from typing import Any, Optional, Sequence

from warden.ghost import load_findings, scan
from warden.models import Transformation, defects_from_ghost

from . import __version__
from .seat import Drafter

EXIT_PROPOSED, EXIT_NOTHING, EXIT_USAGE, EXIT_NO_FINDINGS = 0, 1, 2, 3

_BASELINE = "drafter-dry-run"


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="drafter",
        description="The in-loop maker. Proposes one fix for a Ghost Tools finding, as data. Never writes.",
        epilog="exit codes: 0 proposal made, 1 nothing to propose, 2 usage error, 3 findings could not be obtained",
    )
    parser.add_argument("--version", action="version", version=f"drafter {__version__}")
    sub = parser.add_subparsers(dest="command", metavar="COMMAND")
    sub.required = True
    propose = sub.add_parser(
        "propose", help="dry run: print the edit the Drafter would propose for a folder, as JSON",
        description="Read-only. Prints the proposed edits and the reasons findings were skipped, as JSON.")
    propose.add_argument("path", metavar="PATH", help="the folder Ghost Tools scanned")
    source = propose.add_mutually_exclusive_group()
    source.add_argument("--findings", metavar="FILE", type=Path,
                        help="a saved Ghost Tools JSON report, instead of a scan (with neither option: exit 3)")
    source.add_argument("--ghost-root", metavar="DIR", type=Path,
                        help="a Ghost Tools checkout (the folder holding the ghost_buster package) to scan with")
    propose.add_argument("--scope", choices=("code", "documentation"), default=None,
                         help="the grant's scope, as Warden would set it (default: any)")
    propose.add_argument("-v", "--verbose", action="count", default=0,
                         help="log to stderr: -v for INFO, -vv for DEBUG (refusals and tracebacks)")
    return parser


def _configure_logging(verbosity: int) -> None:
    level = logging.WARNING if verbosity <= 0 else logging.INFO if verbosity == 1 else logging.DEBUG
    logging.basicConfig(stream=sys.stderr, level=level, force=True,
                        format="drafter: %(levelname)s: %(name)s: %(message)s")


def _proposal_json(proposal: Transformation) -> dict[str, Any]:
    return {
        "intent": proposal.intent,
        "scope": proposal.transformation_scope,
        "affected_files": list(proposal.affected_files),
        "expected_behavior": proposal.expected_behavior,
        "evidence": list(proposal.evidence),
        "edits": [{"path": e.path, "kind": e.kind, "old": e.old, "new": e.new} for e in proposal.edits],
    }


def _propose(args: argparse.Namespace) -> int:
    target = Path(args.path)
    if not target.is_dir():
        print(f"drafter: {args.path}: not a folder", file=sys.stderr)
        return EXIT_USAGE
    log = logging.getLogger("drafter.cli")
    try:
        if args.findings is not None:
            found: Sequence[dict[str, Any]] = load_findings(args.findings)
        else:
            found = scan(target, ghost_tools_root=args.ghost_root)
        observed = defects_from_ghost(found)
    except (OSError, ValueError, RuntimeError) as err:
        # Ghost's own errors (GhostCrashed, GhostRefused) are RuntimeErrors; a bad JSON file is a ValueError.
        log.debug("could not obtain findings", exc_info=True)
        print(f"drafter: could not obtain findings: {type(err).__name__}: {err}", file=sys.stderr)
        print("drafter: pass --findings FILE (a Ghost JSON report) or --ghost-root DIR", file=sys.stderr)
        return EXIT_NO_FINDINGS
    drafter = Drafter(scope=args.scope)
    proposal = drafter.propose(target, observed, _BASELINE)
    report = {
        "drafter_version": __version__,
        "target": str(target.resolve()),
        "findings": len(observed),
        "proposal": _proposal_json(proposal) if proposal is not None else None,
        "skipped": [{"finding": fid, "reason": reason} for fid, reason in drafter.last_skipped],
    }
    print(json.dumps(report, indent=2, sort_keys=True))
    return EXIT_PROPOSED if proposal is not None else EXIT_NOTHING


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = _parser().parse_args(argv)       # argparse exits with 2 on a usage error, and 0 after --version
    _configure_logging(getattr(args, "verbose", 0))
    return _propose(args)


if __name__ == "__main__":
    sys.exit(main())
