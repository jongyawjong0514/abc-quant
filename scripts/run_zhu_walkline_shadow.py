"""Run the Zhu walkline shadow advisory scanner."""

from __future__ import annotations

import argparse
from datetime import date
from pathlib import Path
import shutil
import sqlite3
import sys

import yaml


REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

def main(argv: list[str] | None = None) -> int:
    from abc_quant.data.local_tw_loader import load_future_price_rows, load_local_tw_bundle
    from abc_quant.data.web_cache import WebSourceCache
    from abc_quant.data.web_research import collect_web_research
    from abc_quant.features.market_rotation import load_concept_stock_map
    from abc_quant.reports.zhu_walkline_report import write_zhu_walkline_outputs
    from abc_quant.signals.zhu_walkline_shadow import (
        build_zhu_walkline_shadow_result,
        compute_forward_evaluation,
    )
    from scripts.score_zhu_walkline_daily_shadow_strength import (
        main as score_strength_main,
    )
    from scripts.score_zhu_walkline_early_lowpoint import (
        main as score_early_lowpoint_main,
    )

    args = _parse_args(argv)
    config = _load_yaml(REPO_ROOT / args.config)
    if args.output_dir:
        config.setdefault("data", {})["output_dir"] = args.output_dir

    top_n = int(args.top_n or config.get("runtime", {}).get("default_top_n", 30))
    _assert_explicit_asof_available(config, args.asof, stock_id=args.stock)
    bundle = load_local_tw_bundle(config, asof=args.asof, stock_id=args.stock)
    if args.asof != "latest" and str(bundle.asof_date) != args.asof:
        raise RuntimeError(
            "explicit --asof must not fall back to another market date: "
            f"requested={args.asof}, loaded={bundle.asof_date}"
        )
    concept_map = load_concept_stock_map(REPO_ROOT / "config" / "concept_stock_map.yaml")
    web_records: list[dict[str, object]] = []
    if args.use_web:
        cache = WebSourceCache(REPO_ROOT / config.get("data", {}).get("web_cache_dir", "data/web_cache"))
        web_records = collect_web_research(
            config,
            bundle.stock_info,
            asof_date=bundle.asof_date,
            max_results=int(args.web_max_results),
            cache=cache,
        )

    result = build_zhu_walkline_shadow_result(
        bundle,
        concept_map=concept_map,
        web_records=web_records,
        top_n=top_n,
        web_research_used=bool(args.use_web),
        config=config,
    )

    evaluation_frame = None
    evaluation_summary = None
    if args.evaluate_forward:
        stock_ids = sorted(
            set(result.top_rise_candidates["stock_id"].astype(str))
            | set(result.top_fall_risks["stock_id"].astype(str))
        )
        future_prices = load_future_price_rows(
            config["data"]["sqlite_path"],
            asof_date=result.asof_date,
            stock_ids=stock_ids,
        )
        evaluation_frame, evaluation_summary = compute_forward_evaluation(result, future_prices)

    outputs = write_zhu_walkline_outputs(
        result,
        bundle.data_quality,
        output_dir=REPO_ROOT / config.get("data", {}).get("output_dir", "reports/zhu_walkline_shadow"),
        evaluation_frame=evaluation_frame,
        evaluation_summary=evaluation_summary,
    )
    output_dir = REPO_ROOT / config.get(
        "data", {}
    ).get("output_dir", "reports/zhu_walkline_shadow")
    if _shadow_strength_report_enabled(config, skip=args.skip_shadow_strength_report):
        strength_config = config.get("shadow_strength_report", {})
        rules_csv = str(
            strength_config.get(
                "rules_csv", "config/zhu_walkline_shadow_strength_rules.csv"
            )
        )
        score_strength_main(
            [
                "--asof",
                result.asof_date,
                "--config",
                args.config,
                "--scanner-dir",
                str(output_dir),
                "--output-dir",
                str(output_dir),
                "--rules-csv",
                rules_csv,
            ]
        )
        for suffix, output_key in [
            ("csv", "shadow_strength_csv"),
            ("json", "shadow_strength_json"),
            ("md", "shadow_strength_markdown"),
        ]:
            dated_path = output_dir / (
                f"{result.asof_date}_zhu_walkline_shadow_strength.{suffix}"
            )
            latest_path = output_dir / f"latest_zhu_walkline_shadow_strength.{suffix}"
            shutil.copyfile(dated_path, latest_path)
            outputs[f"{result.asof_date}_{output_key}"] = dated_path
            outputs[f"latest_{output_key}"] = latest_path
        trajectory_dated_path = output_dir / (
            f"{result.asof_date}_zhu_walkline_shadow_strength_trajectory.csv"
        )
        trajectory_latest_path = (
            output_dir / "latest_zhu_walkline_shadow_strength_trajectory.csv"
        )
        shutil.copyfile(trajectory_dated_path, trajectory_latest_path)
        outputs[f"{result.asof_date}_shadow_strength_trajectory_csv"] = (
            trajectory_dated_path
        )
        outputs["latest_shadow_strength_trajectory_csv"] = trajectory_latest_path

    if _early_lowpoint_report_enabled(
        config, skip=args.skip_early_lowpoint_report
    ):
        score_early_lowpoint_main(
            [
                "--asof",
                result.asof_date,
                "--config",
                args.config,
                "--scanner-dir",
                str(output_dir),
                "--output-dir",
                str(output_dir),
            ]
        )
        for suffix, output_key in [
            ("csv", "early_lowpoint_csv"),
            ("json", "early_lowpoint_json"),
            ("md", "early_lowpoint_markdown"),
        ]:
            dated_path = output_dir / (
                f"{result.asof_date}_zhu_walkline_early_lowpoint.{suffix}"
            )
            latest_path = output_dir / f"latest_zhu_walkline_early_lowpoint.{suffix}"
            outputs[f"{result.asof_date}_{output_key}"] = dated_path
            outputs[f"latest_{output_key}"] = latest_path

    if args.verbose:
        for key, path in sorted(outputs.items()):
            print(f"{key}: {path}")
    else:
        print(f"asof_date={result.asof_date}")
        print(f"mode={result.mode}")
        print(f"formal_champion_changed={result.formal_champion_changed}")
        print(f"formal_trade_effect={result.formal_trade_effect}")
        print(f"web_research_used={result.web_research_used}")
        print(f"output_dir={REPO_ROOT / config.get('data', {}).get('output_dir', 'reports/zhu_walkline_shadow')}")
    return 0


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--asof", default="latest")
    parser.add_argument("--top-n", type=int, default=None)
    parser.add_argument("--stock", default=None)
    web_group = parser.add_mutually_exclusive_group()
    web_group.add_argument("--use-web", dest="use_web", action="store_true")
    web_group.add_argument("--no-web", dest="use_web", action="store_false")
    parser.set_defaults(use_web=False)
    parser.add_argument("--web-max-results", type=int, default=5)
    parser.add_argument("--evaluate-forward", action="store_true")
    parser.add_argument("--skip-shadow-strength-report", action="store_true")
    parser.add_argument("--skip-early-lowpoint-report", action="store_true")
    parser.add_argument("--output-dir", default=None)
    parser.add_argument("--config", default="config/zhu_walkline_shadow.yaml")
    parser.add_argument("--verbose", action="store_true")
    return parser.parse_args(argv)


def _shadow_strength_report_enabled(
    config: dict[str, object],
    *,
    skip: bool,
) -> bool:
    if skip:
        return False
    strength_config = config.get("shadow_strength_report", {})
    return bool(
        isinstance(strength_config, dict) and strength_config.get("enabled", True)
    )


def _early_lowpoint_report_enabled(
    config: dict[str, object],
    *,
    skip: bool,
) -> bool:
    if skip:
        return False
    early_config = config.get("early_lowpoint_report", {})
    return bool(isinstance(early_config, dict) and early_config.get("enabled", True))


def _load_yaml(path: Path) -> dict[str, object]:
    if not path.exists():
        raise FileNotFoundError(f"config file not found: {path}")
    with path.open("r", encoding="utf-8") as fh:
        data = yaml.safe_load(fh) or {}
    if not isinstance(data, dict):
        raise ValueError(f"config root must be a mapping: {path}")
    return data


def _assert_explicit_asof_available(
    config: dict[str, object],
    asof: str,
    *,
    stock_id: str | None = None,
) -> None:
    """Fail closed before report writes when an explicit market date is unavailable."""
    if asof == "latest":
        return

    try:
        parsed_asof = date.fromisoformat(asof)
    except ValueError as exc:
        raise ValueError(f"--asof must be latest or YYYY-MM-DD: {asof}") from exc
    if parsed_asof.isoformat() != asof:
        raise ValueError(f"--asof must be latest or YYYY-MM-DD: {asof}")

    data_config = config.get("data", {})
    if not isinstance(data_config, dict):
        raise ValueError("config data section must be a mapping")
    sqlite_value = data_config.get("sqlite_path")
    if not isinstance(sqlite_value, str) or not sqlite_value.strip():
        raise ValueError("config data.sqlite_path must be a non-empty path")
    sqlite_path = Path(sqlite_value)
    if not sqlite_path.is_absolute():
        sqlite_path = REPO_ROOT / sqlite_path
    if not sqlite_path.exists():
        raise FileNotFoundError(f"market SQLite file not found: {sqlite_path}")

    required_tables = ("daily_ohlcv_features", "tw_adjusted_ohlcv_daily")
    missing_tables: list[str] = []
    predicate = "date = ?"
    parameters: tuple[str, ...] = (asof,)
    if stock_id:
        predicate += " AND stock_id = ?"
        parameters += (str(stock_id),)

    try:
        with sqlite3.connect(str(sqlite_path)) as connection:
            connection.execute("PRAGMA query_only = ON")
            for table in required_tables:
                row = connection.execute(
                    f"SELECT 1 FROM {table} WHERE {predicate} LIMIT 1",
                    parameters,
                ).fetchone()
                if row is None:
                    missing_tables.append(table)
    except sqlite3.Error as exc:
        raise RuntimeError(f"unable to verify explicit --asof in {sqlite_path}: {exc}") from exc

    if missing_tables:
        stock_context = f", stock_id={stock_id}" if stock_id else ""
        raise RuntimeError(
            "explicit --asof is unavailable; refusing to fall back or overwrite latest "
            f"outputs: requested={asof}{stock_context}, "
            f"missing_tables={','.join(missing_tables)}"
        )


if __name__ == "__main__":
    raise SystemExit(main())
