"""CLI for deterministic modeling smoke diagnostics."""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence
from typing import TextIO

from abc_quant.pipeline.modeling import (
    DEFAULT_BASELINE_METHOD,
    DEFAULT_TRAIN_END,
    DEFAULT_VALIDATION_END,
    run_baseline_modeling_smoke,
)


def main(argv: Sequence[str] | None = None) -> int:
    """Print deterministic modeling smoke diagnostics as JSON."""
    return _run(argv, stdout=sys.stdout, stderr=sys.stderr)


def _run(
    argv: Sequence[str] | None,
    *,
    stdout: TextIO,
    stderr: TextIO,
) -> int:
    parser = _build_parser()
    try:
        args = parser.parse_args(argv)
    except SystemExit as exc:
        return int(exc.code)

    try:
        summary = run_baseline_modeling_smoke(
            train_end=args.train_end,
            validation_end=args.validation_end,
            method=args.method,
        )
    except Exception as exc:
        print(f"error: {exc}", file=stderr)
        return 1

    json.dump(summary, stdout, indent=args.indent, sort_keys=True)
    stdout.write("\n")
    return 0


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m abc_quant.cli.modeling_smoke",
        description="Print deterministic baseline modeling smoke diagnostics as JSON.",
    )
    parser.add_argument(
        "--train-end",
        default=DEFAULT_TRAIN_END,
        help=f"Last train date boundary. Default: {DEFAULT_TRAIN_END}.",
    )
    parser.add_argument(
        "--validation-end",
        default=DEFAULT_VALIDATION_END,
        help=f"Last validation date boundary. Default: {DEFAULT_VALIDATION_END}.",
    )
    parser.add_argument(
        "--method",
        choices=("mean", "median"),
        default=DEFAULT_BASELINE_METHOD,
        help=f"Constant-baseline method. Default: {DEFAULT_BASELINE_METHOD}.",
    )
    parser.add_argument(
        "--indent",
        type=int,
        default=None,
        help="Optional JSON indentation.",
    )
    return parser


if __name__ == "__main__":
    raise SystemExit(main())
