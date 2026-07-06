"""CLI for deterministic LightGBM dependency smoke diagnostics."""

from __future__ import annotations

import argparse
import json
import sys
from typing import TextIO

from abc_quant.pipeline import run_lightgbm_dependency_smoke


def main(argv: list[str] | None = None) -> int:
    """Print deterministic LightGBM dependency smoke diagnostics as JSON."""
    return _run(argv, stdout=sys.stdout, stderr=sys.stderr)


def _run(
    argv: list[str] | None,
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
        summary = run_lightgbm_dependency_smoke()
    except Exception as exc:
        print(f"error: {exc}", file=stderr)
        return 1

    json.dump(summary, stdout, indent=args.indent, sort_keys=True)
    stdout.write("\n")
    return 0


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m abc_quant.cli.lightgbm_dependency_smoke",
        description="Print deterministic LightGBM dependency smoke diagnostics as JSON.",
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
