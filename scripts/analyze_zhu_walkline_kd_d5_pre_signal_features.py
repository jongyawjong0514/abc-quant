"""Compare strictly pre-signal local chip, holder, margin, and volume features.

This research sidecar uses all labeled Zhu walkline KD rows as the rank universe
and the requested three outcome groups only for evaluator-side validation.  It
never changes signal membership.  All feature sources are filtered to rows
strictly before the signal date, while D+5 returns remain evaluator-only.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sqlite3
from typing import Any

import numpy as np
import pandas as pd
import yaml

from abc_quant.features.pre_signal_features import (
    NUMERIC_PRE_SIGNAL_FEATURES,
    build_pre_signal_feature_frame,
    build_univariate_holdout_reference,
    compare_gain_groups_with_loss,
    summarize_feature_groups,
)
from abc_quant.features.shadow_strength import (
    apply_shadow_strength_score,
    build_shadow_strength_rules,
    evaluate_shadow_strength_holdout,
    rules_frame,
    strength_monotonicity,
)


REPO_ROOT = Path(__file__).resolve().parents[1]

FEATURE_LABELS = {
    "pre_return_1d_pct": "訊號前一交易日報酬(%)",
    "pre_return_5d_pct": "訊號前5日報酬(%)",
    "pre_return_20d_pct": "訊號前20日報酬(%)",
    "pre_close_to_sma20_pct": "訊號前收盤相對月線(%)",
    "pre_range_pos_20": "訊號前20日區間位置",
    "pre_day_volume_ratio_20": "訊號前一日20日量比",
    "pre5_mean_day_volume_ratio_20": "訊號前5日平均量比",
    "pre5_max_day_volume_ratio_20": "訊號前5日最高量比",
    "pre5_min_abs_open_close_pct": "訊號前5日最小開收差(%)",
    "pre5_tight_body_count_le_1_2pct": "訊號前5日窄幅K棒次數(<=1.2%)",
    "pre5_mean_turnover_million_twd": "訊號前5日平均成交額(百萬元)",
    "pre5_upper_tail_count": "訊號前5日上影供給次數",
    "pre5_volume_exhaustion_count": "訊號前5日量能衰竭次數",
    "pre5_late_chase_count": "訊號前5日追價風險次數",
    "pre_foreign_net_shares_1d": "訊號前一日外資買賣超(股)",
    "pre_foreign_net_shares_5d": "訊號前5日外資買賣超(股)",
    "pre_foreign_net_volume_ratio_1d_pct": "訊號前一日外資買賣超/成交量(%)",
    "pre_foreign_net_volume_ratio_5d_pct": "訊號前5日外資買賣超/成交量(%)",
    "pre_trust_net_volume_ratio_5d_pct": "訊號前5日投信買賣超/成交量(%)",
    "pre_dealer_net_volume_ratio_5d_pct": "訊號前5日自營商買賣超/成交量(%)",
    "pre_institutional_net_volume_ratio_5d_pct": "訊號前5日三大法人買賣超/成交量(%)",
    "pre_foreign_positive_day_ratio_5d": "訊號前5日外資買超日比例",
    "pre_institutional_positive_day_ratio_5d": "訊號前5日法人買超日比例",
    "pre_main_force_net_lots_1d": "訊號前一日主力買賣超proxy(張)",
    "pre_main_force_net_lots_5d": "訊號前5日主力買賣超proxy(張)",
    "pre_main_force_net_volume_ratio_5d_pct": "訊號前5日主力proxy/成交量(%)",
    "pre_main_force_positive_day_ratio_5d": "訊號前5日主力proxy買超日比例",
    "pre_broker_count_diff_1d": "訊號前一日買賣家數差proxy",
    "pre_broker_count_diff_5d_sum": "訊號前5日買賣家數差proxy總和",
    "pre_holder_lag_days": "千張大戶資料延遲(日)",
    "pre_big_holder_ratio_1000_lots_pct": "千張以上大戶持股比例(%)",
    "pre_big_holder_ratio_delta_1w_pctpt": "千張大戶持股比例1週變化(百分點)",
    "pre_big_holder_ratio_delta_4w_pctpt": "千張大戶持股比例4週變化(百分點)",
    "pre_big_holder_count_delta_1w": "千張大戶人數1週變化",
    "pre_big_holder_count_delta_4w": "千張大戶人數4週變化",
    "pre_margin_balance": "訊號前融資餘額",
    "pre_margin_balance_change_5d_pct": "訊號前融資餘額5日變化(%)",
    "pre_margin_balance_change_20d_pct": "訊號前融資餘額20日變化(%)",
}


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    config = _load_yaml(_repo_path(args.config))
    input_csv = _repo_path(args.input_csv)
    ranking_input_csv = _repo_path(args.ranking_input_csv)
    cooldown_csv = _repo_path(args.cooldown_csv)
    output_dir = _repo_path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    sqlite_path = Path(config["data"]["sqlite_path"])
    finlab_root = Path(config["data"]["finlab_items_root"])
    if not sqlite_path.exists():
        raise FileNotFoundError(f"SQLite database not found: {sqlite_path}")
    if not finlab_root.exists():
        raise FileNotFoundError(f"FinLab items root not found: {finlab_root}")

    signals = pd.read_csv(input_csv, dtype={"stock_id": str})
    signals = _prepare_grouped_signals(signals)
    ranking_signals = pd.read_csv(ranking_input_csv, dtype={"stock_id": str})
    ranking_signals = _prepare_grouped_signals(ranking_signals)
    grouped_keys = set(_key_series(signals))
    ranking_keys = set(_key_series(ranking_signals))
    if not grouped_keys.issubset(ranking_keys):
        raise ValueError("ranking input does not contain every grouped signal key")
    cooldown_keys = _load_cooldown_keys(cooldown_csv)
    stock_ids = sorted(ranking_signals["stock_id"].unique())
    start_date = (
        pd.to_datetime(ranking_signals["asof_date"]).min() - pd.Timedelta(days=150)
    ).date()
    end_date = (
        pd.to_datetime(ranking_signals["asof_date"]).max() - pd.Timedelta(days=1)
    ).date()

    histories = load_local_histories(
        sqlite_path,
        stock_ids=stock_ids,
        start_date=start_date.isoformat(),
        end_date=end_date.isoformat(),
    )
    main_force_path = finlab_root / "main_force_chip" / "主力買賣超.pkl"
    broker_count_path = finlab_root / "main_force_chip" / "買賣家數差.pkl"
    main_force = load_wide_panel(
        main_force_path,
        stock_ids=stock_ids,
        start_date=start_date.isoformat(),
        end_date=end_date.isoformat(),
    )
    broker_count = load_wide_panel(
        broker_count_path,
        stock_ids=stock_ids,
        start_date=start_date.isoformat(),
        end_date=end_date.isoformat(),
    )

    feature_frame = build_pre_signal_feature_frame(
        ranking_signals,
        price_history=histories["price"],
        institutional_history=histories["institutional"],
        holder_history=histories["holder"],
        margin_history=histories["margin"],
        main_force_panel=main_force,
        broker_count_panel=broker_count,
    )
    enriched = signals.merge(feature_frame, on=["asof_date", "stock_id"], how="left")
    ranking_enriched = ranking_signals.merge(
        feature_frame, on=["asof_date", "stock_id"], how="left"
    )
    assert_no_lookahead(enriched)
    assert_no_lookahead(ranking_enriched)
    enriched["same_stock_cooldown"] = _key_series(enriched).isin(cooldown_keys)
    enriched["corporate_action_event_in_horizon"] = _as_bool(
        enriched["corporate_action_event_in_horizon"]
    )

    scopes = {
        "all_events": enriched,
        "no_corporate_action": enriched[
            ~enriched["corporate_action_event_in_horizon"]
        ],
        "same_stock_cooldown": enriched[enriched["same_stock_cooldown"]],
        "no_corp_same_stock_cooldown": enriched[
            (~enriched["corporate_action_event_in_horizon"])
            & enriched["same_stock_cooldown"]
        ],
    }
    group_stats = pd.concat(
        [summarize_feature_groups(rows, scope=scope) for scope, rows in scopes.items()],
        ignore_index=True,
    )
    pairwise = pd.concat(
        [
            compare_gain_groups_with_loss(rows, scope=scope)
            for scope, rows in scopes.items()
        ],
        ignore_index=True,
    )
    robust_contrasts = build_robust_contrasts(pairwise)
    holdout_reference = build_univariate_holdout_reference(
        scopes["no_corp_same_stock_cooldown"],
        discovery_end=args.discovery_end,
        holdout_start=args.holdout_start,
        min_discovery_class_rows=args.min_discovery_class_rows,
        min_holdout_selected_rows=args.min_holdout_selected_rows,
    )
    shadow_strength_rules = build_shadow_strength_rules(holdout_reference)
    enriched = apply_shadow_strength_score(enriched, rules=shadow_strength_rules)
    ranking_enriched = apply_shadow_strength_score(
        ranking_enriched, rules=shadow_strength_rules
    )
    scopes = {
        "all_events": enriched,
        "no_corporate_action": enriched[
            ~enriched["corporate_action_event_in_horizon"]
        ],
        "same_stock_cooldown": enriched[enriched["same_stock_cooldown"]],
        "no_corp_same_stock_cooldown": enriched[
            (~enriched["corporate_action_event_in_horizon"])
            & enriched["same_stock_cooldown"]
        ],
    }
    shadow_strength_rule_table = rules_frame(shadow_strength_rules)
    shadow_strength_validation = evaluate_shadow_strength_holdout(
        scopes["no_corp_same_stock_cooldown"],
        holdout_start=args.holdout_start,
    )
    shadow_strength_ranked = ranking_enriched.sort_values(
        ["asof_date", "shadow_strength_score", "stock_id"],
        ascending=[True, False, True],
        na_position="last",
    )
    latest_rankable_date = ranking_enriched.loc[
        ranking_enriched["shadow_strength_complete"], "asof_date"
    ].max()
    shadow_strength_latest = shadow_strength_ranked[
        shadow_strength_ranked["asof_date"].eq(latest_rankable_date)
    ]
    feature_coverage = build_feature_coverage(enriched)
    source_audit = build_source_audit(
        enriched,
        histories=histories,
        main_force=main_force,
        broker_count=broker_count,
        sqlite_path=sqlite_path,
        main_force_path=main_force_path,
        broker_count_path=broker_count_path,
        table_ranges=load_table_date_ranges(sqlite_path),
    )
    summary = build_summary(
        enriched=enriched,
        scopes=scopes,
        group_stats=group_stats,
        robust_contrasts=robust_contrasts,
        holdout_reference=holdout_reference,
        shadow_strength_rules=shadow_strength_rule_table,
        shadow_strength_validation=shadow_strength_validation,
        shadow_strength_ranked=shadow_strength_ranked,
        feature_coverage=feature_coverage,
        source_audit=source_audit,
        args=args,
    )
    write_outputs(
        output_dir,
        enriched=enriched,
        group_stats=group_stats,
        pairwise=pairwise,
        robust_contrasts=robust_contrasts,
        holdout_reference=holdout_reference,
        shadow_strength_rules=shadow_strength_rule_table,
        shadow_strength_validation=shadow_strength_validation,
        shadow_strength_ranked=shadow_strength_ranked,
        shadow_strength_latest=shadow_strength_latest,
        feature_coverage=feature_coverage,
        source_audit=source_audit,
        summary=summary,
    )

    print("mode=shadow_observation_only")
    print("formal_champion_changed=False")
    print("formal_trade_effect=False")
    print("promotion_decision=blocked_before_promotion_review")
    print(f"enriched_rows={len(enriched)}")
    print(f"shadow_strength_ranking_universe_rows={len(shadow_strength_ranked)}")
    print(
        "shadow_strength_cumulative_monotonic="
        f"{strength_monotonicity(shadow_strength_validation, view='cumulative_min_score')['all_pass']}"
    )
    print(f"summary_md={output_dir / 'zhu_walkline_kd_d5_pre_signal_summary.md'}")
    return 0


def load_local_histories(
    sqlite_path: Path,
    *,
    stock_ids: list[str],
    start_date: str,
    end_date: str,
) -> dict[str, pd.DataFrame]:
    """Load bounded histories required by the pre-signal feature builder."""
    table_specs = {
        "price": (
            "daily_ohlcv_features",
            "date",
            [
                "date",
                "stock_id",
                "open",
                "close",
                "volume",
                "sma20_gap",
                "range_pos_20",
                "day_volume_ratio_20",
                "upper_tail_flag",
                "volume_exhaustion_flag",
                "late_chase_risk_flag",
            ],
        ),
        "institutional": (
            "tw_institutional_flow_moving_averages_price_aligned_daily",
            "date",
            [
                "date",
                "stock_id",
                "foreign_net_buy_shares",
                "trust_net_buy_shares",
                "dealer_net_buy_shares",
                "institutional_net_buy_shares",
                "flow_available",
                "flow_source",
            ],
        ),
        "holder": (
            "tw_tdcc_holder_moving_averages_price_aligned_daily",
            "date",
            [
                "date",
                "stock_id",
                "holder_source_date",
                "holder_lag_days",
                "alignment_status",
                "big_holder_count_1000_lots",
                "big_holder_ratio_1000_lots_pct",
                "source_kind",
                "source_quality",
            ],
        ),
        "margin": (
            "tw_margin_balance_history",
            "trade_date",
            [
                "trade_date",
                "stock_id",
                "margin_balance",
                "available_date",
                "source_name",
            ],
        ),
    }
    output: dict[str, pd.DataFrame] = {}
    with sqlite3.connect(sqlite_path) as connection:
        tables = {
            row[0]
            for row in connection.execute("select name from sqlite_master where type='table'")
        }
        for key, (table, date_column, columns) in table_specs.items():
            if table not in tables:
                output[key] = pd.DataFrame(columns=columns)
                continue
            output[key] = _read_bounded_table(
                connection,
                table=table,
                date_column=date_column,
                columns=columns,
                stock_ids=stock_ids,
                start_date=start_date,
                end_date=end_date,
            )
    return output


def load_wide_panel(
    path: Path,
    *,
    stock_ids: list[str],
    start_date: str,
    end_date: str,
) -> pd.DataFrame:
    """Load a local FinLab-compatible wide panel and keep the requested slice."""
    if not path.exists():
        return pd.DataFrame()
    panel = pd.read_pickle(path)
    if not isinstance(panel, pd.DataFrame):
        raise TypeError(f"Expected pandas DataFrame in {path}")
    panel.index = pd.to_datetime(panel.index, errors="coerce")
    panel.columns = [str(column).zfill(4) for column in panel.columns]
    available = [stock_id for stock_id in stock_ids if stock_id in panel.columns]
    return panel.loc[
        (panel.index >= pd.Timestamp(start_date)) & (panel.index <= pd.Timestamp(end_date)),
        available,
    ].copy()


def load_table_date_ranges(sqlite_path: Path) -> dict[str, tuple[str | None, str | None]]:
    """Read freshness boundaries for audit-only sources that are not used."""
    specs = {
        "tw_official_institutional_trading_daily": "trade_date",
        "finlab_broker_count_diff_history": "date",
    }
    output: dict[str, tuple[str | None, str | None]] = {}
    with sqlite3.connect(sqlite_path) as connection:
        tables = {
            row[0]
            for row in connection.execute("select name from sqlite_master where type='table'")
        }
        for table, date_column in specs.items():
            if table not in tables:
                output[table] = (None, None)
                continue
            row = connection.execute(
                f'select min("{date_column}"), max("{date_column}") from "{table}"'
            ).fetchone()
            output[table] = (
                _date_text(row[0]) if row else None,
                _date_text(row[1]) if row else None,
            )
    return output


def assert_no_lookahead(rows: pd.DataFrame) -> None:
    """Fail if any exported source date is on or after its signal date."""
    signal_date = pd.to_datetime(rows["asof_date"], errors="raise")
    source_columns = [
        column
        for column in rows.columns
        if column.startswith("pre_") and column.endswith("_date")
    ]
    violations: list[str] = []
    for column in source_columns:
        source_date = pd.to_datetime(rows[column], errors="coerce")
        count = int((source_date.notna() & source_date.ge(signal_date)).sum())
        if count:
            violations.append(f"{column}={count}")
    if violations:
        raise AssertionError("pre-signal no-lookahead violation: " + ", ".join(violations))


def build_robust_contrasts(pairwise: pd.DataFrame) -> pd.DataFrame:
    """Keep a primary contrast plus direction consistency across robustness scopes."""
    if pairwise.empty:
        return pd.DataFrame()
    records: list[dict[str, Any]] = []
    grouped = pairwise.groupby(["target_group", "feature"], sort=False)
    for (target_group, feature), group in grouped:
        primary = group[group["scope"].eq("no_corp_same_stock_cooldown")]
        if primary.empty:
            continue
        row = primary.iloc[0]
        signs = np.sign(pd.to_numeric(group["median_difference"], errors="coerce").dropna())
        nonzero_signs = {int(sign) for sign in signs if sign != 0}
        records.append(
            {
                "target_group": target_group,
                "target_group_label": row["target_group_label"],
                "feature": feature,
                "feature_label": FEATURE_LABELS.get(feature, feature),
                "target_rows": int(row["target_rows"]),
                "loss_rows": int(row["reference_rows"]),
                "target_coverage": row["target_coverage"],
                "loss_coverage": row["reference_coverage"],
                "target_median": row["target_median"],
                "loss_median": row["reference_median"],
                "median_difference": row["median_difference"],
                "mean_difference": row["mean_difference"],
                "standardized_mean_difference": row["standardized_mean_difference"],
                "scope_count": int(group["scope"].nunique()),
                "direction_consistent": len(nonzero_signs) <= 1 and len(nonzero_signs) == 1,
                "mean_median_direction_agree": _same_nonzero_sign(
                    row["median_difference"], row["mean_difference"]
                ),
            }
        )
    output = pd.DataFrame(records)
    if output.empty:
        return output
    output["absolute_standardized_difference"] = pd.to_numeric(
        output["standardized_mean_difference"], errors="coerce"
    ).abs()
    return output.sort_values(
        ["target_group", "direction_consistent", "absolute_standardized_difference"],
        ascending=[True, False, False],
    ).reset_index(drop=True)


def build_feature_coverage(rows: pd.DataFrame) -> pd.DataFrame:
    records: list[dict[str, Any]] = []
    for feature in NUMERIC_PRE_SIGNAL_FEATURES:
        values = pd.to_numeric(rows.get(feature), errors="coerce")
        for group_key, index in rows.groupby("d5_group", sort=False).groups.items():
            group_values = values.loc[index]
            records.append(
                {
                    "d5_group": group_key,
                    "feature": feature,
                    "feature_label": FEATURE_LABELS.get(feature, feature),
                    "rows": int(len(group_values)),
                    "available_rows": int(group_values.notna().sum()),
                    "coverage": float(group_values.notna().mean()),
                }
            )
    return pd.DataFrame(records)


def build_source_audit(
    enriched: pd.DataFrame,
    *,
    histories: dict[str, pd.DataFrame],
    main_force: pd.DataFrame,
    broker_count: pd.DataFrame,
    sqlite_path: Path,
    main_force_path: Path,
    broker_count_path: Path,
    table_ranges: dict[str, tuple[str | None, str | None]],
) -> pd.DataFrame:
    specs = [
        (
            "price_volume",
            "daily_ohlcv_features",
            sqlite_path,
            histories["price"],
            "date",
            "pre_day_volume_ratio_20",
            "used",
            "strict date < signal_date",
        ),
        (
            "institutional_flow",
            "tw_institutional_flow_moving_averages_price_aligned_daily",
            sqlite_path,
            histories["institutional"],
            "date",
            "pre_foreign_net_volume_ratio_5d_pct",
            "used_hybrid_history",
            "strict date < signal_date and flow_available=1",
        ),
        (
            "main_force_proxy",
            "main_force_chip/主力買賣超.pkl",
            main_force_path,
            main_force,
            "index",
            "pre_main_force_net_volume_ratio_5d_pct",
            "used_proxy_not_true_holder",
            "strict index < signal_date",
        ),
        (
            "broker_count_proxy",
            "main_force_chip/買賣家數差.pkl",
            broker_count_path,
            broker_count,
            "index",
            "pre_broker_count_diff_5d_sum",
            "used_proxy_from_fresh_pickle",
            "strict index < signal_date; stale DB mirror not used",
        ),
        (
            "large_holder",
            "tw_tdcc_holder_moving_averages_price_aligned_daily",
            sqlite_path,
            histories["holder"],
            "date",
            "pre_big_holder_ratio_1000_lots_pct",
            "used_quality_filtered",
            "strict date and holder_source_date < signal_date; alignment_status=ok",
        ),
        (
            "margin",
            "tw_margin_balance_history",
            sqlite_path,
            histories["margin"],
            "trade_date",
            "pre_margin_balance_change_5d_pct",
            "used",
            "strict trade_date and available_date < signal_date",
        ),
    ]
    records: list[dict[str, Any]] = []
    for domain, source, path, frame, date_column, anchor, status, rule in specs:
        if date_column == "index":
            source_min = frame.index.min() if not frame.empty else pd.NaT
            source_max = frame.index.max() if not frame.empty else pd.NaT
            loaded_rows = int(frame.notna().any(axis=1).sum()) if not frame.empty else 0
        else:
            dates = pd.to_datetime(frame.get(date_column), errors="coerce")
            source_min = dates.min()
            source_max = dates.max()
            loaded_rows = int(len(frame))
        available = pd.to_numeric(enriched.get(anchor), errors="coerce").notna()
        records.append(
            {
                "domain": domain,
                "source": source,
                "path": str(path),
                "source_min_date_loaded": _date_text(source_min),
                "source_max_date_loaded": _date_text(source_max),
                "loaded_rows_or_dates": loaded_rows,
                "signal_rows": int(len(enriched)),
                "signal_rows_available": int(available.sum()),
                "signal_coverage": float(available.mean()),
                "status": status,
                "point_in_time_rule": rule,
            }
        )
    official_min, official_max = table_ranges.get(
        "tw_official_institutional_trading_daily", (None, None)
    )
    records.append(
        {
            "domain": "official_institutional_audit",
            "source": "tw_official_institutional_trading_daily",
            "path": str(sqlite_path),
            "source_min_date_loaded": official_min,
            "source_max_date_loaded": official_max,
            "loaded_rows_or_dates": None,
            "signal_rows": int(len(enriched)),
            "signal_rows_available": None,
            "signal_coverage": None,
            "status": "audit_only_incomplete_2026H1",
            "point_in_time_rule": "not used because local history begins after signal window start",
        }
    )
    broker_min, broker_max = table_ranges.get("finlab_broker_count_diff_history", (None, None))
    records.append(
        {
            "domain": "broker_db_mirror_audit",
            "source": "finlab_broker_count_diff_history",
            "path": str(sqlite_path),
            "source_min_date_loaded": broker_min,
            "source_max_date_loaded": broker_max,
            "loaded_rows_or_dates": None,
            "signal_rows": int(len(enriched)),
            "signal_rows_available": None,
            "signal_coverage": None,
            "status": "audit_only_stale_fresh_pickle_used",
            "point_in_time_rule": "stale DB mirror excluded; fresh wide pickle used instead",
        }
    )
    return pd.DataFrame(records)


def build_summary(
    *,
    enriched: pd.DataFrame,
    scopes: dict[str, pd.DataFrame],
    group_stats: pd.DataFrame,
    robust_contrasts: pd.DataFrame,
    holdout_reference: pd.DataFrame,
    shadow_strength_rules: pd.DataFrame,
    shadow_strength_validation: pd.DataFrame,
    shadow_strength_ranked: pd.DataFrame,
    feature_coverage: pd.DataFrame,
    source_audit: pd.DataFrame,
    args: argparse.Namespace,
) -> dict[str, Any]:
    top_contrasts = robust_contrasts[
        robust_contrasts["direction_consistent"]
        & robust_contrasts["mean_median_direction_agree"]
        & robust_contrasts["target_coverage"].ge(0.5)
        & robust_contrasts["loss_coverage"].ge(0.5)
    ].groupby("target_group", group_keys=False).head(10)
    top_holdout = holdout_reference[
        holdout_reference["meets_min_holdout_rows"]
        & holdout_reference["holdout_lift"].gt(1.0)
    ].sort_values(["task", "holdout_lift"], ascending=[True, False])
    top_holdout = top_holdout.groupby("task", group_keys=False).head(10)
    primary = scopes["no_corp_same_stock_cooldown"]
    holdout = primary[
        pd.to_datetime(primary["asof_date"]).ge(pd.Timestamp(args.holdout_start))
    ]
    primary_complete = primary["shadow_strength_complete"].astype(bool)
    holdout_complete = holdout["shadow_strength_complete"].astype(bool)
    ranking_complete = shadow_strength_ranked["shadow_strength_complete"].astype(bool)
    cumulative_monotonicity = strength_monotonicity(
        shadow_strength_validation, view="cumulative_min_score"
    )
    exact_monotonicity = strength_monotonicity(
        shadow_strength_validation, view="exact_score"
    )
    return {
        "mode": "shadow_observation_only",
        "formal_champion_changed": False,
        "formal_trade_effect": False,
        "promotion_decision": "blocked_before_promotion_review",
        "market": "Taiwan equities",
        "currency": "TWD",
        "timezone": "Asia/Taipei",
        "signal_start": str(enriched["asof_date"].min()),
        "signal_end": str(enriched["asof_date"].max()),
        "horizon": "fifth subsequent stock trading-day adjusted close",
        "target_groups": {
            key: int(value)
            for key, value in enriched["d5_group"].value_counts().sort_index().items()
        },
        "scope_rows": {key: int(len(value)) for key, value in scopes.items()},
        "discovery_end": args.discovery_end,
        "holdout_start": args.holdout_start,
        "feature_count": len(NUMERIC_PRE_SIGNAL_FEATURES),
        "source_audit": _records(source_audit),
        "domain_comparison": build_domain_comparison(group_stats),
        "top_robust_contrasts": _records(top_contrasts),
        "top_holdout_references": _records(top_holdout),
        "shadow_strength": {
            "score_version": "kd_d5_pre_signal_shadow_strength_v1",
            "reference_task": "D5_GAIN_GE10_VS_LOSS",
            "formula": "four equal-weight point-in-time components at 25 points each",
            "included_components": [
                "main_force",
                "no_upper_tail",
                "volume_ratio",
                "margin_change",
            ],
            "explicitly_excluded_inputs": [
                "pre_margin_balance",
                "pre_foreign_net_shares_1d",
                "pre_foreign_net_shares_5d",
            ],
            "missing_value_policy": "INSUFFICIENT_FEATURES; no zero fill and no rank",
            "ranking_universe_policy": (
                "all H1 signals, including 0% to <10% and immature outcome rows; "
                "future labels do not select rank membership"
            ),
            "rules": _records(shadow_strength_rules),
            "ranking_universe_rows": int(len(shadow_strength_ranked)),
            "ranking_complete_rows": int(ranking_complete.sum()),
            "ranking_complete_coverage": float(ranking_complete.mean()),
            "primary_rows": int(len(primary)),
            "primary_complete_rows": int(primary_complete.sum()),
            "primary_complete_coverage": float(primary_complete.mean()),
            "holdout_rows": int(len(holdout)),
            "holdout_complete_rows": int(holdout_complete.sum()),
            "holdout_complete_coverage": float(holdout_complete.mean()),
            "cumulative_monotonicity": cumulative_monotonicity,
            "exact_score_monotonicity": exact_monotonicity,
            "latest_rankable_signal_date": str(
                shadow_strength_ranked.loc[ranking_complete, "asof_date"].max()
            ),
        },
        "shadow_strength_validation": _records(shadow_strength_validation),
        "minimum_feature_coverage": _records(
            feature_coverage.sort_values("coverage").head(10)
        ),
        "no_lookahead": (
            "Every source date is strictly earlier than signal_date; signal-day and future "
            "rows are excluded from feature construction."
        ),
        "corporate_action_handling": (
            "Primary predictive reference excludes rows flagged with a D+5 adjustment-factor "
            "change; all-events comparisons remain for audit."
        ),
        "cost_slippage_note": (
            "Not applied: this is a feature-screen against signal-close-to-D+5-close outcome "
            "groups, not an executable entry/exit backtest."
        ),
        "multiple_testing_note": (
            "Many univariate features are compared. Jan-Mar thresholds and Apr-Jun holdout "
            "results are research triage only and require an independent future OOS period."
        ),
    }


def build_domain_comparison(group_stats: pd.DataFrame) -> list[dict[str, Any]]:
    """Return a small domain-focused table from the primary robustness scope."""
    primary = group_stats[group_stats["scope"].eq("no_corp_same_stock_cooldown")]
    specs = [
        ("tight_body_count", "pre5_tight_body_count_le_1_2pct"),
        ("prior_5d_mean_volume_ratio", "pre5_mean_day_volume_ratio_20"),
        ("foreign_5d_net_volume_ratio_pct", "pre_foreign_net_volume_ratio_5d_pct"),
        ("main_force_1d_net_lots_proxy", "pre_main_force_net_lots_1d"),
        ("main_force_5d_net_volume_ratio_pct", "pre_main_force_net_volume_ratio_5d_pct"),
        ("big_holder_ratio_pct", "pre_big_holder_ratio_1000_lots_pct"),
        ("big_holder_ratio_4w_delta_pctpt", "pre_big_holder_ratio_delta_4w_pctpt"),
        ("margin_balance_5d_change_pct", "pre_margin_balance_change_5d_pct"),
    ]
    records: list[dict[str, Any]] = []
    for domain_metric, feature in specs:
        feature_rows = primary[primary["feature"].eq(feature)].set_index("d5_group")
        if feature_rows.empty:
            continue
        record: dict[str, Any] = {
            "metric": domain_metric,
            "feature": feature,
            "feature_label": FEATURE_LABELS.get(feature, feature),
        }
        for group, prefix in [
            ("D5_LOSS", "loss"),
            ("D5_GAIN_10_20", "gain_10_20"),
            ("D5_GAIN_GE_20", "gain_ge_20"),
        ]:
            if group not in feature_rows.index:
                record[f"{prefix}_median"] = None
                record[f"{prefix}_coverage"] = None
                continue
            row = feature_rows.loc[group]
            record[f"{prefix}_median"] = row["median"]
            record[f"{prefix}_coverage"] = row["coverage"]
        records.append(record)
    return _json_safe(records)


def write_outputs(
    output_dir: Path,
    *,
    enriched: pd.DataFrame,
    group_stats: pd.DataFrame,
    pairwise: pd.DataFrame,
    robust_contrasts: pd.DataFrame,
    holdout_reference: pd.DataFrame,
    shadow_strength_rules: pd.DataFrame,
    shadow_strength_validation: pd.DataFrame,
    shadow_strength_ranked: pd.DataFrame,
    shadow_strength_latest: pd.DataFrame,
    feature_coverage: pd.DataFrame,
    source_audit: pd.DataFrame,
    summary: dict[str, Any],
) -> None:
    outputs = {
        "zhu_walkline_kd_d5_pre_signal_rows.csv": enriched,
        "zhu_walkline_kd_d5_pre_signal_group_stats.csv": group_stats,
        "zhu_walkline_kd_d5_pre_signal_pairwise.csv": pairwise,
        "zhu_walkline_kd_d5_pre_signal_robust_contrasts.csv": robust_contrasts,
        "zhu_walkline_kd_d5_pre_signal_holdout_reference.csv": holdout_reference,
        "zhu_walkline_kd_d5_shadow_strength_rules.csv": shadow_strength_rules,
        "zhu_walkline_kd_d5_shadow_strength_validation.csv": (
            shadow_strength_validation
        ),
        "zhu_walkline_kd_d5_shadow_strength_ranked_rows.csv": (
            shadow_strength_ranked
        ),
        "zhu_walkline_kd_d5_shadow_strength_latest.csv": shadow_strength_latest,
        "zhu_walkline_kd_d5_pre_signal_feature_coverage.csv": feature_coverage,
        "zhu_walkline_kd_d5_pre_signal_source_audit.csv": source_audit,
    }
    for name, frame in outputs.items():
        _safe_csv(frame, output_dir / name)
    (output_dir / "zhu_walkline_kd_d5_pre_signal_summary.json").write_text(
        json.dumps(_json_safe(summary), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    (output_dir / "zhu_walkline_kd_d5_pre_signal_summary.md").write_text(
        render_markdown(summary), encoding="utf-8"
    )


def render_markdown(summary: dict[str, Any]) -> str:
    lines = [
        "# Zhu Walkline KD D+5 訊號日前特徵比較",
        "",
        "## 研究邊界",
        "",
        f"- 訊號期間：`{summary['signal_start']}` ～ `{summary['signal_end']}`",
        "- 市場／幣別／時區：台股／TWD／Asia/Taipei",
        "- 所有特徵日期嚴格 `< signal_date`，不使用訊號日或 D+1～D+5 資料。",
        "- D+5 調整收盤報酬只作 evaluator label，不回灌訊號。",
        "- 主力與買賣家數差標示為 proxy，不視為真實大戶持股。",
        "",
        "## 樣本",
        "",
        "| scope | rows |",
        "|---|---:|",
    ]
    for scope, rows in summary["scope_rows"].items():
        lines.append(f"| {scope} | {rows} |")
    strength = summary["shadow_strength"]
    lines.extend(
        [
            "",
            "## 四項影子強度分數（0～100）",
            "",
            "四項各 25 分；門檻只用 2026-01～03 發現期決定，2026-04～06 "
            "只作固定門檻驗證。任何一項缺資料即標記 `INSUFFICIENT_FEATURES`，"
            "不補零、不排名。",
            "",
            "| component | pre-signal feature | rule | points |",
            "|---|---|---:|---:|",
        ]
    )
    for row in strength["rules"]:
        operator = ">=" if row["direction"] == "HIGHER" else "<="
        lines.append(
            f"| {row['component']} | {FEATURE_LABELS.get(row['feature'], row['feature'])} | "
            f"{operator} {_num(row['threshold'])} | {row['points']} |"
        )
    lines.extend(
        [
            "",
            f"- 排名母體（含 0～<10% 與尚未成熟結果）："
            f"{strength['ranking_complete_rows']} / {strength['ranking_universe_rows']} "
            f"可評分（{_pct(strength['ranking_complete_coverage'])}）。",
            f"- 主要樣本完整覆蓋：{strength['primary_complete_rows']} / "
            f"{strength['primary_rows']}（{_pct(strength['primary_complete_coverage'])}）。",
            f"- Apr-Jun holdout 完整覆蓋：{strength['holdout_complete_rows']} / "
            f"{strength['holdout_rows']}（{_pct(strength['holdout_complete_coverage'])}）。",
            "- 明確不納入：原始融資餘額、外資買賣超原始股數。",
            "- 未來 D+5 分組只用於門檻驗證，不用於決定排名母體。",
            "",
            "### Apr-Jun 累積強度驗證",
            "",
            "`score >= 門檻` 採累積觀察；lift 以四項資料完整的 holdout 全樣本為基準。",
            "",
            "| score >= | rows | >=10% | >=20% | loss | avg D+5 | median D+5 | lift >=10% |",
            "|---:|---:|---:|---:|---:|---:|---:|---:|",
        ]
    )
    for row in summary["shadow_strength_validation"]:
        if row["view"] != "cumulative_min_score":
            continue
        lines.append(
            f"| {_num(row['score_threshold'])} | {row['selected_rows']} | "
            f"{_pct(row['d5_gain_ge10_rate'])} | {_pct(row['d5_gain_ge20_rate'])} | "
            f"{_pct(row['d5_loss_rate'])} | {_pct(row['avg_d5_adjusted_return_pct'] / 100)} | "
            f"{_pct(row['median_d5_adjusted_return_pct'] / 100)} | "
            f"{_num(row['gain_ge10_lift_vs_complete'])} |"
        )
    cumulative_status = strength["cumulative_monotonicity"]["all_pass"]
    exact_status = strength["exact_score_monotonicity"]["all_pass"]
    lines.extend(
        [
            "",
            f"- 累積門檻單調性（>=10%、>=20%、loss 三項同時）：`{cumulative_status}`。",
            f"- 單一精確分箱完整單調性：`{exact_status}`；因此分數目前是排序器，"
            "不是已校準勝率。",
            "- `>=75` 僅作高強度 shadow 參考，不是交易 gate；其報酬中位數仍需"
            "在獨立未來樣本與成本模型中驗證。",
        ]
    )
    lines.extend(
        [
            "",
            "## 資料來源與覆蓋率",
            "",
            "| domain | source max | coverage | status |",
            "|---|---|---:|---|",
        ]
    )
    for row in summary["source_audit"]:
        lines.append(
            f"| {row['domain']} | {row['source_max_date_loaded']} | "
            f"{_pct(row['signal_coverage'])} | {row['status']} |"
        )
    lines.extend(
        [
            "",
            "## 外資／主力／大戶／量價重點對照",
            "",
            "主要 scope 為排除公司行動且同股 5 日 cooldown；表內為各組中位數。",
            "",
            "| feature | loss | +10%~<20% | >=20% | target coverage |",
            "|---|---:|---:|---:|---:|",
        ]
    )
    for row in summary["domain_comparison"]:
        target_coverage = min(
            value
            for value in [
                row.get("gain_10_20_coverage"),
                row.get("gain_ge_20_coverage"),
            ]
            if value is not None
        )
        lines.append(
            f"| {row['feature_label']} | {_num(row['loss_median'])} | "
            f"{_num(row['gain_10_20_median'])} | {_num(row['gain_ge_20_median'])} | "
            f"{_pct(target_coverage)} |"
        )
    lines.extend(
        [
            "",
            "## 穩健組間差異",
            "",
            "以下只列 all-events、排除公司行動、同股 cooldown、兩者合併四個 scope "
            "中位數方向一致、主要 scope 的平均與中位數方向相同，且覆蓋率至少 50% "
            "的前十項。這是描述性差異，不是因果關係或正式選股規則。",
            "",
            "| target | feature | target median | loss median | diff | std diff |",
            "|---|---|---:|---:|---:|---:|",
        ]
    )
    for row in summary["top_robust_contrasts"]:
        lines.append(
            f"| {row['target_group']} | {row['feature_label']} | "
            f"{_num(row['target_median'])} | {_num(row['loss_median'])} | "
            f"{_num(row['median_difference'])} | "
            f"{_num(row['standardized_mean_difference'])} |"
        )
    lines.extend(
        [
            "",
            "## Jan-Mar 發現、Apr-Jun 固定門檻參考",
            "",
            "每個特徵只在 2026-01～03 決定方向與中位數中點門檻，再套用 "
            "2026-04～06。只使用排除公司行動且同股 5 日 cooldown 的樣本。多重比較"
            "尚未校正，因此只能做下一輪特徵優先順序。",
            "",
            "| task | feature | direction | threshold | selected | precision | lift |",
            "|---|---|---|---:|---:|---:|---:|",
        ]
    )
    for row in summary["top_holdout_references"]:
        lines.append(
            f"| {row['task']} | {FEATURE_LABELS.get(row['feature'], row['feature'])} | "
            f"{row['direction']} | {_num(row['threshold'])} | "
            f"{row['holdout_selected_rows']} | {_pct(row['holdout_precision'])} | "
            f"{_num(row['holdout_lift'])} |"
        )
    lines.extend(
        [
            "",
            "## 限制與決策",
            "",
            "- 2026H1 僅六個月，4 月市場狀態對高報酬組有明顯干擾。",
            "- 官方法人日表在本機只自 2026-05-26 起；H1 使用的是 "
            "`hybrid_finlab_history_twse_tpex_official_overlay`，來源邊界已保留。",
            "- TDCC 為週資料並對齊交易日；缺失、stale 或無來源的列不補零。",
            "- 外資原始股數與占成交量比例在部分組別方向相反，顯示股本／流動性尺度"
            "干擾，不能直接用原始買超股數跨股票比較。",
            "- 窄幅 K 棒是既有訊號前置 gate；在已通過 gate 的樣本內，較多窄幅 K 棒"
            "沒有帶來額外 holdout lift。",
            "- 成交成本與滑價未套用，因為本分析沒有定義可成交進出場。",
            "- 下一步需以 2026-07 之後的獨立成熟樣本做預先登記 OOS，"
            "再決定是否建立多變量機率 sidecar。",
            "",
            "```text",
            "mode=shadow_observation_only",
            "formal_champion_changed=False",
            "formal_trade_effect=False",
            "promotion_decision=blocked_before_promotion_review",
            "```",
            "",
        ]
    )
    return "\n".join(lines)


def _read_bounded_table(
    connection: sqlite3.Connection,
    *,
    table: str,
    date_column: str,
    columns: list[str],
    stock_ids: list[str],
    start_date: str,
    end_date: str,
) -> pd.DataFrame:
    placeholders = ",".join("?" for _ in stock_ids)
    select_columns = ", ".join(f'"{column}"' for column in columns)
    query = f"""
        select {select_columns}
        from "{table}"
        where "{date_column}" between ? and ?
          and stock_id in ({placeholders})
        order by stock_id, "{date_column}"
    """
    params: list[Any] = [start_date, end_date, *stock_ids]
    return pd.read_sql_query(query, connection, params=params)


def _prepare_grouped_signals(rows: pd.DataFrame) -> pd.DataFrame:
    required = {
        "asof_date",
        "stock_id",
        "d5_group",
        "d5_group_label",
        "d5_adjusted_return_pct",
        "corporate_action_event_in_horizon",
    }
    missing = required - set(rows.columns)
    if missing:
        raise ValueError(f"input CSV missing columns: {sorted(missing)}")
    output = rows.copy()
    output["stock_id"] = output["stock_id"].astype(str).str.zfill(4)
    output["asof_date"] = pd.to_datetime(output["asof_date"], errors="raise").dt.strftime(
        "%Y-%m-%d"
    )
    return output.sort_values(["asof_date", "stock_id"]).reset_index(drop=True)


def _load_cooldown_keys(path: Path) -> set[str]:
    rows = pd.read_csv(path, dtype={"stock_id": str})
    rows["stock_id"] = rows["stock_id"].astype(str).str.zfill(4)
    rows["asof_date"] = pd.to_datetime(rows["asof_date"]).dt.strftime("%Y-%m-%d")
    return set(_key_series(rows))


def _key_series(rows: pd.DataFrame) -> pd.Series:
    return rows["asof_date"].astype(str) + "|" + rows["stock_id"].astype(str)


def _load_yaml(path: Path) -> dict[str, Any]:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def _repo_path(value: str) -> Path:
    path = Path(value)
    return path if path.is_absolute() else REPO_ROOT / path


def _as_bool(values: pd.Series) -> pd.Series:
    if pd.api.types.is_bool_dtype(values):
        return values.fillna(False)
    return values.astype(str).str.lower().isin({"1", "true", "yes"})


def _records(frame: pd.DataFrame) -> list[dict[str, Any]]:
    return _json_safe(frame.to_dict(orient="records"))


def _same_nonzero_sign(left: Any, right: Any) -> bool:
    left_number = pd.to_numeric(pd.Series([left]), errors="coerce").iloc[0]
    right_number = pd.to_numeric(pd.Series([right]), errors="coerce").iloc[0]
    if pd.isna(left_number) or pd.isna(right_number):
        return False
    return bool(left_number != 0 and right_number != 0 and np.sign(left_number) == np.sign(right_number))


def _json_safe(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_json_safe(item) for item in value]
    if isinstance(value, (np.bool_, bool)):
        return bool(value)
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating, float)):
        return float(value) if np.isfinite(value) else None
    if pd.isna(value):
        return None
    return value


def _safe_csv(frame: pd.DataFrame, path: Path) -> None:
    output = frame.copy()
    for column in output.select_dtypes(include=["object", "string"]).columns:
        output[column] = output[column].fillna("")
    output.to_csv(path, index=False, encoding="utf-8-sig", na_rep="")


def _date_text(value: Any) -> str | None:
    parsed = pd.to_datetime(value, errors="coerce")
    return parsed.strftime("%Y-%m-%d") if pd.notna(parsed) else None


def _num(value: Any) -> str:
    number = pd.to_numeric(pd.Series([value]), errors="coerce").iloc[0]
    return f"{float(number):.4f}" if pd.notna(number) else ""


def _pct(value: Any) -> str:
    number = pd.to_numeric(pd.Series([value]), errors="coerce").iloc[0]
    return f"{float(number) * 100:.2f}%" if pd.notna(number) else ""


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default="config/zhu_walkline_shadow.yaml")
    parser.add_argument(
        "--input-csv",
        default=(
            "reports/zhu_walkline_kd_d5_groups_2026_01_06/"
            "zhu_walkline_kd_d5_grouped_rows.csv"
        ),
    )
    parser.add_argument(
        "--ranking-input-csv",
        default=(
            "reports/zhu_walkline_kd_d5_groups_2026_01_06/"
            "zhu_walkline_kd_d5_labeled_rows.csv"
        ),
    )
    parser.add_argument(
        "--cooldown-csv",
        default=(
            "reports/zhu_walkline_kd_d5_groups_2026_01_06/"
            "zhu_walkline_kd_d5_cooldown_rows.csv"
        ),
    )
    parser.add_argument(
        "--output-dir",
        default="reports/zhu_walkline_kd_d5_pre_signal_features_2026_01_06",
    )
    parser.add_argument("--discovery-end", default="2026-03-31")
    parser.add_argument("--holdout-start", default="2026-04-01")
    parser.add_argument("--min-discovery-class-rows", type=int, default=15)
    parser.add_argument("--min-holdout-selected-rows", type=int, default=15)
    return parser.parse_args(argv)


if __name__ == "__main__":
    raise SystemExit(main())
