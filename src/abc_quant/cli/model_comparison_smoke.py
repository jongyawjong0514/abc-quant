"""CLI for deterministic model-comparison smoke diagnostics."""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence
from typing import TextIO

from abc_quant.pipeline.model_comparison import (
    DEFAULT_MODEL_COMPARISON_BASELINE_METHOD,
    DEFAULT_MODEL_COMPARISON_TRAIN_END,
    DEFAULT_MODEL_COMPARISON_VALIDATION_END,
    run_model_comparison_smoke,
)


def main(argv: Sequence[str] | None = None) -> int:
    """Print deterministic model-comparison smoke diagnostics as JSON."""
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
        summary = run_model_comparison_smoke(
            train_end=args.train_end,
            validation_end=args.validation_end,
            baseline_method=args.baseline_method,
        )
    except Exception as exc:
        print(f"error: {exc}", file=stderr)
        return 1

    json.dump(summary, stdout, indent=args.indent, sort_keys=True)
    stdout.write("\n")
    return 0


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m abc_quant.cli.model_comparison_smoke",
        description="Print deterministic model-comparison smoke diagnostics as JSON.",
    )
    parser.add_argument(
        "--train-end",
        default=DEFAULT_MODEL_COMPARISON_TRAIN_END,
        help=(
            "Last train date boundary. "
            f"Default: {DEFAULT_MODEL_COMPARISON_TRAIN_END}."
        ),
    )
    parser.add_argument(
        "--validation-end",
        default=DEFAULT_MODEL_COMPARISON_VALIDATION_END,
        help=(
            "Last validation date boundary. "
            f"Default: {DEFAULT_MODEL_COMPARISON_VALIDATION_END}."
        ),
    )
    parser.add_argument(
        "--baseline-method",
        choices=("mean", "median"),
        default=DEFAULT_MODEL_COMPARISON_BASELINE_METHOD,
        help=(
            "Constant-baseline reference method. "
            f"Default: {DEFAULT_MODEL_COMPARISON_BASELINE_METHOD}."
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
