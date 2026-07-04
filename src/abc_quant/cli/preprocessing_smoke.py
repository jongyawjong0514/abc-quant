"""CLI for deterministic preprocessing smoke diagnostics."""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence
from typing import TextIO

from abc_quant.pipeline.preprocessing import (
    DEFAULT_PREPROCESSING_TRAIN_END,
    DEFAULT_PREPROCESSING_VALIDATION_END,
    run_preprocessing_smoke,
)


def main(argv: Sequence[str] | None = None) -> int:
    """Print deterministic preprocessing smoke diagnostics as JSON."""
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
        summary = run_preprocessing_smoke(
            train_end=args.train_end,
            validation_end=args.validation_end,
        )
    except Exception as exc:
        print(f"error: {exc}", file=stderr)
        return 1

    json.dump(summary, stdout, indent=args.indent, sort_keys=True)
    stdout.write("\n")
    return 0


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m abc_quant.cli.preprocessing_smoke",
        description="Print deterministic preprocessing smoke diagnostics as JSON.",
    )
    parser.add_argument(
        "--train-end",
        default=DEFAULT_PREPROCESSING_TRAIN_END,
        help=f"Last train date boundary. Default: {DEFAULT_PREPROCESSING_TRAIN_END}.",
    )
    parser.add_argument(
        "--validation-end",
        default=DEFAULT_PREPROCESSING_VALIDATION_END,
        help=(
            "Last validation date boundary. "
            f"Default: {DEFAULT_PREPROCESSING_VALIDATION_END}."
        ),
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
