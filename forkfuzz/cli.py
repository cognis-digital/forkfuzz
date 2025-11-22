"""Command-line interface for FORKFUZZ.

Examples
--------
Run the bundled demo and print a table::

    python -m forkfuzz check demos/01-basic/vault.json

Machine-readable output for CI (exit code is non-zero on any finding)::

    python -m forkfuzz check demos/01-basic/vault.json --format json

Reproduce / tune the search::

    python -m forkfuzz check spec.json --runs 2000 --seq-len 40 --seed 7
"""

from __future__ import annotations

import argparse
import json
import sys
from typing import List, Optional

from forkfuzz import TOOL_NAME, TOOL_VERSION
from forkfuzz.core import SpecError, fuzz, load_spec


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="forkfuzz",
        description=(
            "FORKFUZZ - one-command invariant fuzzing for contract specs. "
            "Runs generated call sequences against a JSON spec and reports "
            "the smallest sequence that breaks an invariant."
        ),
        epilog=(
            "example: python -m forkfuzz check demos/01-basic/vault.json\n"
            "example: python -m forkfuzz check spec.json --format json --seed 7"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--version", action="version", version=f"{TOOL_NAME} {TOOL_VERSION}"
    )
    parser.add_argument(
        "--format",
        choices=["table", "json"],
        default="table",
        help="output format (default: table)",
    )

    sub = parser.add_subparsers(dest="command")

    check = sub.add_parser(
        "check",
        help="fuzz a contract spec for invariant violations",
        description="Fuzz a JSON contract spec and report counterexamples.",
    )
    check.add_argument("spec", help="path to a JSON contract spec")
    check.add_argument(
        "--runs", type=int, default=500, help="number of random sequences (default: 500)"
    )
    check.add_argument(
        "--seq-len",
        type=int,
        default=25,
        help="max calls per sequence (default: 25)",
    )
    check.add_argument(
        "--seed", type=int, default=0, help="PRNG seed for reproducibility (default: 0)"
    )
    check.add_argument(
        "--all",
        action="store_true",
        help="keep searching for violations of every invariant, not just the first",
    )
    return parser


def _render_table(report) -> str:
    lines: List[str] = []
    lines.append(f"FORKFUZZ {TOOL_VERSION}  spec={report.spec_name!r}")
    lines.append(
        f"  runs={report.runs} seq_len={report.seq_len} seed={report.seed} "
        f"calls_executed={report.calls_executed} "
        f"invariants={report.invariants_checked}"
    )
    lines.append("-" * 60)
    if not report.findings:
        lines.append("PASS: no invariant violations found.")
        return "\n".join(lines)
    lines.append(f"FAIL: {len(report.findings)} invariant(s) broken.")
    for f in report.findings:
        lines.append("")
        lines.append(f"  [BROKEN] {f.invariant}: {f.expr}")
        lines.append(f"  found after {f.runs_executed} run(s); minimal counterexample:")
        if not f.sequence:
            lines.append("    (violated by the initial state)")
        for i, call in enumerate(f.sequence):
            lines.append(f"    {i + 1}. {call.as_text()}")
        lines.append(f"  final state: {f.state}")
    return "\n".join(lines)


def main(argv: Optional[List[str]] = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    if args.command is None:
        parser.print_help()
        return 0

    if args.command == "check":
        try:
            spec = load_spec(args.spec)
        except FileNotFoundError:
            print(f"error: spec file not found: {args.spec}", file=sys.stderr)
            return 2
        except SpecError as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 2

        try:
            report = fuzz(
                spec,
                runs=args.runs,
                seq_len=args.seq_len,
                seed=args.seed,
                stop_on_first=not args.all,
            )
        except SpecError as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 2

        if args.format == "json":
            print(json.dumps(report.to_dict(), indent=2, default=str))
        else:
            print(_render_table(report))

        return 1 if report.failed else 0

    parser.print_help()
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
