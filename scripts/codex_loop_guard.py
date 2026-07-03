"""CLI wrapper for the Codex closed-loop inbox guard."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

from abc_quant.governance.codex_loop import run_guard


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate the current Codex closed-loop task.")
    parser.add_argument("--root", type=Path, default=Path.cwd(), help="Project root.")
    parser.add_argument("--strict", action="store_true", help="Exit nonzero unless status is ready.")
    args = parser.parse_args()

    root = args.root.resolve()
    result = run_guard(root=root)
    print(f"status={result.status}")
    print(f"report={root / 'reports' / 'codex_loop' / 'latest.md'}")

    if args.strict and not result.is_ready:
        return 2
    if result.status in {"blocked_invalid", "blocked_risky"}:
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
