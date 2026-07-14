"""Download Yahoo Taiwan concept groups into an append-only local snapshot DB."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from abc_quant.data.yahoo_concepts import (  # noqa: E402
    YahooConceptSnapshot,
    download_yahoo_concept_snapshot,
    load_important_yahoo_concept_snapshot,
    write_snapshot_exports,
    write_yahoo_concept_snapshot,
)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    config = yaml.safe_load((REPO_ROOT / args.config).read_text(encoding="utf-8")) or {}
    sqlite_path = Path(config["data"]["yahoo_concept_sqlite_path"])
    snapshot = download_yahoo_concept_snapshot(
        max_workers=args.max_workers,
        timeout_seconds=args.timeout_seconds,
        retries=args.retries,
    )
    inserted = write_yahoo_concept_snapshot(snapshot, sqlite_path=sqlite_path)
    if not inserted:
        persisted_manifest, _ = load_important_yahoo_concept_snapshot(
            sqlite_path,
            snapshot_id=str(snapshot.manifest["snapshot_id"]),
        )
        snapshot = YahooConceptSnapshot(
            persisted_manifest,
            snapshot.categories,
            snapshot.membership,
        )
    export_dir = REPO_ROOT / args.output_dir / snapshot.manifest["snapshot_id"]
    write_snapshot_exports(snapshot, output_dir=export_dir)
    reference_dir = REPO_ROOT / args.reference_dir / snapshot.manifest["snapshot_id"]
    write_snapshot_exports(snapshot, output_dir=reference_dir)

    print(json.dumps(snapshot.manifest, ensure_ascii=False, indent=2, sort_keys=True))
    print(f"inserted={inserted}")
    print(f"sqlite_path={sqlite_path}")
    print(f"export_dir={export_dir}")
    print(f"reference_dir={reference_dir}")
    print("mode=shadow_observation_only")
    print("formal_champion_changed=False")
    print("formal_trade_effect=False")
    return 0


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default="config/zhu_walkline_shadow.yaml")
    parser.add_argument("--output-dir", default="reports/yahoo_concept_membership")
    parser.add_argument("--reference-dir", default="data/reference/yahoo_concepts")
    parser.add_argument("--max-workers", type=int, default=4)
    parser.add_argument("--timeout-seconds", type=int, default=30)
    parser.add_argument("--retries", type=int, default=3)
    return parser.parse_args(argv)


if __name__ == "__main__":
    raise SystemExit(main())
