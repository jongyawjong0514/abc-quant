"""Score one Zhu walkline as-of date with the frozen four-component shadow rank."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any

import numpy as np
import pandas as pd
import yaml

from abc_quant.features.pre_signal_features import build_pre_signal_feature_frame
from abc_quant.features.shadow_strength import (
    SCORE_VERSION,
    ShadowStrengthRule,
    apply_shadow_strength_score,
)


REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

EXPECTED_COMPONENTS = {
    "main_force",
    "no_upper_tail",
    "volume_ratio",
    "margin_change",
}

TRAJECTORY_SCOPE = "retrospective_confirmed_candidates"
TRAJECTORY_EXPORT_COLUMNS = [
    "signal_date",
    "asof_date",
    "stock_id",
    "stock_name",
    "lead_days",
    "relative_day",
    "trajectory_history_status",
    "trajectory_available_prior_days",
    "trajectory_expected_prior_days",
    "trajectory_scope",
    "trajectory_live_deployable",
    "trajectory_rank_status",
    "pre_price_source_date",
    "pre_main_force_source_date",
    "pre_margin_available_date",
    "pre_main_force_net_lots_1d",
    "pre5_upper_tail_count",
    "pre_day_volume_ratio_20",
    "pre_margin_balance_change_5d_pct",
    "shadow_strength_main_force_pass",
    "shadow_strength_no_upper_tail_pass",
    "shadow_strength_volume_ratio_pass",
    "shadow_strength_margin_change_pass",
    "shadow_strength_main_force_points",
    "shadow_strength_no_upper_tail_points",
    "shadow_strength_volume_ratio_points",
    "shadow_strength_margin_change_points",
    "shadow_strength_available_components",
    "shadow_strength_passed_components",
    "shadow_strength_complete",
    "shadow_strength_score",
    "shadow_strength_tier",
    "shadow_strength_score_status",
    "shadow_strength_missing_components",
    "shadow_strength_passed_component_names",
    "shadow_strength_feature_available_date",
    "shadow_strength_rank_within_signal_date",
    "shadow_strength_rank_pct_within_signal_date",
    "shadow_strength_rankable_count",
    "shadow_strength_score_version",
    "shadow_strength_mode",
    "shadow_strength_formal_trade_effect",
]


def main(argv: list[str] | None = None) -> int:
    from scripts.analyze_zhu_walkline_kd_d5_pre_signal_features import (
        assert_no_lookahead,
        load_local_histories,
        load_wide_panel,
    )

    args = _parse_args(argv)
    asof_date = pd.Timestamp(args.asof).strftime("%Y-%m-%d")
    config = _load_yaml(_repo_path(args.config))
    scanner_dir = _repo_path(args.scanner_dir)
    output_dir = _repo_path(args.output_dir or args.scanner_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    feature_matrix_path = scanner_dir / f"{asof_date}_zhu_walkline_feature_matrix.parquet"
    summary_path = scanner_dir / f"{asof_date}_zhu_walkline_summary.json"
    if not feature_matrix_path.exists():
        raise FileNotFoundError(f"scanner feature matrix not found: {feature_matrix_path}")
    if not summary_path.exists():
        raise FileNotFoundError(f"scanner summary not found: {summary_path}")

    scanner_rows = pd.read_parquet(feature_matrix_path)
    candidates = select_daily_confirmation_candidates(scanner_rows, asof_date=asof_date)
    scanner_summary = json.loads(summary_path.read_text(encoding="utf-8"))
    market = scanner_summary.get("market", {})
    rules = load_frozen_rules(_repo_path(args.rules_csv))
    strength_config = config.get("shadow_strength_report", {})
    trajectory_enabled = bool(strength_config.get("trajectory_enabled", True))
    trajectory_lookback = int(
        strength_config.get("trajectory_lookback_trading_days", 10)
    )
    if trajectory_lookback < 0:
        raise ValueError("trajectory_lookback_trading_days must be non-negative")

    if candidates.empty:
        scored = _empty_scored_frame(candidates)
        trajectory = _empty_trajectory_frame()
    else:
        sqlite_path = Path(config["data"]["sqlite_path"])
        finlab_root = Path(config["data"]["finlab_items_root"])
        stock_ids = sorted(candidates["stock_id"].astype(str).unique())
        start_date = (pd.Timestamp(asof_date) - pd.Timedelta(days=150)).date().isoformat()
        end_date = (pd.Timestamp(asof_date) - pd.Timedelta(days=1)).date().isoformat()
        histories = load_local_histories(
            sqlite_path,
            stock_ids=stock_ids,
            start_date=start_date,
            end_date=end_date,
        )
        main_force = load_wide_panel(
            finlab_root / "main_force_chip" / "主力買賣超.pkl",
            stock_ids=stock_ids,
            start_date=start_date,
            end_date=end_date,
        )
        broker_count = load_wide_panel(
            finlab_root / "main_force_chip" / "買賣家數差.pkl",
            stock_ids=stock_ids,
            start_date=start_date,
            end_date=end_date,
        )
        signal_keys = candidates[["asof_date", "stock_id"]].copy()
        feature_rows = build_pre_signal_feature_frame(
            signal_keys,
            market_calendar=histories["market_calendar"],
            price_history=histories["price"],
            institutional_history=histories["institutional"],
            holder_history=histories["holder"],
            margin_history=histories["margin"],
            main_force_panel=main_force,
            broker_count_panel=broker_count,
        )
        scored = candidates.merge(
            feature_rows,
            on=["asof_date", "stock_id"],
            how="left",
            validate="one_to_one",
        )
        assert_no_lookahead(scored)
        scored = apply_shadow_strength_score(scored, rules=rules)
        if trajectory_enabled:
            trajectory = build_scored_candidate_trajectory(
                candidates,
                market_calendar=histories["market_calendar"],
                price_history=histories["price"],
                institutional_history=histories["institutional"],
                holder_history=histories["holder"],
                margin_history=histories["margin"],
                main_force_panel=main_force,
                broker_count_panel=broker_count,
                rules=rules,
                lookback_trading_days=trajectory_lookback,
            )
            assert_no_lookahead(trajectory)
            assert_signal_day_score_consistency(scored, trajectory)
        else:
            trajectory = _empty_trajectory_frame()

    scored["market_state"] = str(market.get("market_state", "UNKNOWN"))
    scored["market_score"] = market.get("market_score")
    scored["market_risk_score"] = market.get("market_risk_score")
    scored["risk_state"] = np.where(
        scored["market_state"].eq("MARKET_HIGH_RISK_BREAKDOWN"),
        "high_risk_breakdown",
        "shadow_observation",
    )
    scored["action"] = "watch_only"
    scored = scored.sort_values(
        ["shadow_strength_score", "rise_score", "stock_id"],
        ascending=[False, False, True],
        na_position="last",
    ).reset_index(drop=True)

    summary = build_daily_summary(
        scored,
        asof_date=asof_date,
        market=market,
        rules=rules,
        source_feature_matrix=feature_matrix_path,
        trajectory=trajectory,
        trajectory_lookback=trajectory_lookback,
    )
    csv_path = output_dir / f"{asof_date}_zhu_walkline_shadow_strength.csv"
    trajectory_path = (
        output_dir / f"{asof_date}_zhu_walkline_shadow_strength_trajectory.csv"
    )
    json_path = output_dir / f"{asof_date}_zhu_walkline_shadow_strength.json"
    markdown_path = output_dir / f"{asof_date}_zhu_walkline_shadow_strength.md"
    _safe_csv(scored, csv_path)
    _safe_csv(trajectory, trajectory_path)
    json_path.write_text(
        json.dumps(_json_safe(summary), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    markdown_path.write_text(render_markdown(summary), encoding="utf-8")

    print(f"asof_date={asof_date}")
    print(f"candidate_rows={len(scored)}")
    print(f"complete_score_rows={int(scored['shadow_strength_complete'].sum())}")
    print(f"trajectory_rows={len(trajectory)}")
    print(f"trajectory_scope={TRAJECTORY_SCOPE}")
    print("trajectory_live_deployable=False")
    print(f"market_state={market.get('market_state', 'UNKNOWN')}")
    print("mode=shadow_observation_only")
    print("formal_champion_changed=False")
    print("formal_trade_effect=False")
    print(f"csv={csv_path}")
    print(f"trajectory_csv={trajectory_path}")
    print(f"markdown={markdown_path}")
    return 0


def select_daily_confirmation_candidates(
    rows: pd.DataFrame,
    *,
    asof_date: str,
) -> pd.DataFrame:
    """Select fresh same-day KD confirmations without using forward outcomes."""
    required = {
        "asof_date",
        "trade_date",
        "stock_id",
        "stock_name",
        "kd_recovery_confirmation",
    }
    missing = required - set(rows.columns)
    if missing:
        raise ValueError(f"scanner rows missing candidate columns: {sorted(missing)}")
    output = rows.copy()
    output["asof_date"] = pd.to_datetime(output["asof_date"], errors="raise").dt.strftime(
        "%Y-%m-%d"
    )
    output["trade_date"] = pd.to_datetime(
        output["trade_date"], errors="coerce"
    ).dt.strftime("%Y-%m-%d")
    output["stock_id"] = output["stock_id"].astype(str).str.zfill(4)
    confirmed = _as_bool(output["kd_recovery_confirmation"])
    selected = output[
        output["asof_date"].eq(asof_date)
        & output["trade_date"].eq(asof_date)
        & confirmed
    ].copy()
    if selected.duplicated(["asof_date", "stock_id"]).any():
        raise ValueError("duplicate same-day KD confirmation keys")
    return selected.sort_values("stock_id").reset_index(drop=True)


def load_frozen_rules(path: Path) -> list[ShadowStrengthRule]:
    """Load the Jan-Mar discovery rules used by the daily shadow rank."""
    rows = pd.read_csv(path)
    required = {
        "component",
        "feature",
        "source_date_column",
        "direction",
        "threshold",
        "points",
        "reference_task",
        "discovery_end",
    }
    missing = required - set(rows.columns)
    if missing:
        raise ValueError(f"rules CSV missing columns: {sorted(missing)}")
    if set(rows["component"]) != EXPECTED_COMPONENTS or len(rows) != 4:
        raise ValueError("daily shadow strength requires exactly the frozen four components")
    rules = [
        ShadowStrengthRule(
            component=str(row.component),
            feature=str(row.feature),
            source_date_column=str(row.source_date_column),
            direction=str(row.direction),
            threshold=float(row.threshold),
            points=int(row.points),
            reference_task=str(row.reference_task),
            discovery_end=str(row.discovery_end),
        )
        for row in rows.itertuples(index=False)
    ]
    if sum(rule.points for rule in rules) != 100:
        raise ValueError("daily shadow strength rule points must sum to 100")
    return rules


def build_candidate_observation_keys(
    candidates: pd.DataFrame,
    price_history: pd.DataFrame,
    *,
    lookback_trading_days: int = 10,
) -> pd.DataFrame:
    """Build D-N through D keys from each stock's own trading calendar."""
    required = {"asof_date", "stock_id", "stock_name"}
    missing = required - set(candidates.columns)
    if missing:
        raise ValueError(f"candidates missing trajectory columns: {sorted(missing)}")
    if lookback_trading_days < 0:
        raise ValueError("lookback_trading_days must be non-negative")

    history = price_history[["date", "stock_id"]].copy()
    history["date"] = pd.to_datetime(history["date"], errors="coerce")
    history["stock_id"] = history["stock_id"].astype(str).str.zfill(4)
    history = history.dropna(subset=["date"]).drop_duplicates(["date", "stock_id"])
    date_groups = {
        str(stock_id): group["date"].sort_values().drop_duplicates().tolist()
        for stock_id, group in history.groupby("stock_id", sort=False)
    }

    records: list[dict[str, Any]] = []
    normalized = candidates.copy()
    normalized["asof_date"] = pd.to_datetime(
        normalized["asof_date"], errors="raise"
    )
    normalized["stock_id"] = normalized["stock_id"].astype(str).str.zfill(4)
    for row in normalized.itertuples(index=False):
        signal_date = pd.Timestamp(row.asof_date).normalize()
        stock_id = str(row.stock_id)
        prior_dates = [
            pd.Timestamp(value).normalize()
            for value in date_groups.get(stock_id, [])
            if pd.Timestamp(value).normalize() < signal_date
        ][-lookback_trading_days:]
        available = len(prior_dates)
        history_status = (
            "COMPLETE"
            if available == lookback_trading_days
            else "INSUFFICIENT_HISTORY"
        )
        observations = [
            (date, available - index)
            for index, date in enumerate(prior_dates)
        ]
        observations.append((signal_date, 0))
        for observation_date, lead_days in observations:
            records.append(
                {
                    "signal_date": signal_date.strftime("%Y-%m-%d"),
                    "asof_date": observation_date.strftime("%Y-%m-%d"),
                    "stock_id": stock_id,
                    "stock_name": str(row.stock_name),
                    "lead_days": int(lead_days),
                    "relative_day": "D" if lead_days == 0 else f"D-{lead_days}",
                    "trajectory_history_status": history_status,
                    "trajectory_available_prior_days": available,
                    "trajectory_expected_prior_days": lookback_trading_days,
                    "trajectory_scope": TRAJECTORY_SCOPE,
                    "trajectory_live_deployable": False,
                }
            )
    return pd.DataFrame(records)


def build_scored_candidate_trajectory(
    candidates: pd.DataFrame,
    *,
    market_calendar: pd.DataFrame | pd.DatetimeIndex,
    price_history: pd.DataFrame,
    institutional_history: pd.DataFrame,
    holder_history: pd.DataFrame,
    margin_history: pd.DataFrame,
    main_force_panel: pd.DataFrame | None,
    broker_count_panel: pd.DataFrame | None,
    rules: list[ShadowStrengthRule],
    lookback_trading_days: int = 10,
) -> pd.DataFrame:
    """Score the four frozen components for each retrospective trajectory date."""
    keys = build_candidate_observation_keys(
        candidates,
        price_history,
        lookback_trading_days=lookback_trading_days,
    )
    if keys.empty:
        return _empty_trajectory_frame()
    features = build_pre_signal_feature_frame(
        keys[["asof_date", "stock_id"]],
        market_calendar=market_calendar,
        price_history=price_history,
        institutional_history=institutional_history,
        holder_history=holder_history,
        margin_history=margin_history,
        main_force_panel=main_force_panel,
        broker_count_panel=broker_count_panel,
    )
    output = keys.merge(
        features,
        on=["asof_date", "stock_id"],
        how="left",
        validate="one_to_one",
    )
    output = apply_shadow_strength_score(output, rules=rules)
    historical = output["lead_days"].gt(0)
    for column in (
        "shadow_strength_rank_within_signal_date",
        "shadow_strength_rank_pct_within_signal_date",
        "shadow_strength_rankable_count",
    ):
        output.loc[historical, column] = np.nan
    output["trajectory_rank_status"] = np.where(
        historical,
        "WITHHELD_FUTURE_CONDITIONED_UNIVERSE",
        "VALID_SIGNAL_DAY_CANDIDATE_UNIVERSE",
    )
    for column in TRAJECTORY_EXPORT_COLUMNS:
        if column not in output:
            output[column] = np.nan
    return output[TRAJECTORY_EXPORT_COLUMNS].sort_values(
        ["stock_id", "lead_days"], ascending=[True, False]
    ).reset_index(drop=True)


def assert_signal_day_score_consistency(
    scored: pd.DataFrame,
    trajectory: pd.DataFrame,
) -> None:
    """Fail if the trajectory D row differs from the primary same-day score."""
    comparison_columns = [
        "asof_date",
        "stock_id",
        "pre_main_force_net_lots_1d",
        "pre5_upper_tail_count",
        "pre_day_volume_ratio_20",
        "pre_margin_balance_change_5d_pct",
        "shadow_strength_score",
        "shadow_strength_score_status",
        "shadow_strength_passed_component_names",
    ]
    daily = scored[comparison_columns].sort_values("stock_id").reset_index(drop=True)
    signal_day = trajectory.loc[
        trajectory["lead_days"].eq(0), comparison_columns
    ].sort_values("stock_id").reset_index(drop=True)
    pd.testing.assert_frame_equal(daily, signal_day, check_dtype=False)


def build_daily_summary(
    scored: pd.DataFrame,
    *,
    asof_date: str,
    market: dict[str, Any],
    rules: list[ShadowStrengthRule],
    source_feature_matrix: Path,
    trajectory: pd.DataFrame | None = None,
    trajectory_lookback: int = 10,
) -> dict[str, Any]:
    complete = scored["shadow_strength_complete"].astype(bool)
    trajectory_frame = (
        trajectory.copy() if trajectory is not None else _empty_trajectory_frame()
    )
    complete_history_stocks = 0
    if not trajectory_frame.empty:
        complete_history_stocks = int(
            trajectory_frame[
                trajectory_frame["trajectory_history_status"].eq("COMPLETE")
            ]["stock_id"].nunique()
        )
    return {
        "as_of": asof_date,
        "market": "Taiwan equities",
        "currency": "TWD",
        "timezone": "Asia/Taipei",
        "horizon": "shadow ranking only; D+5 validation reference",
        "score_version": SCORE_VERSION,
        "market_state": market.get("market_state", "UNKNOWN"),
        "market_score": market.get("market_score"),
        "market_risk_score": market.get("market_risk_score"),
        "source_feature_matrix": str(source_feature_matrix),
        "candidate_definition": (
            "same-day fresh KD_OVERSOLD_TREND_RECOVERY confirmations; no forward label filter"
        ),
        "candidate_rows": int(len(scored)),
        "complete_score_rows": int(complete.sum()),
        "incomplete_score_rows": int((~complete).sum()),
        "rules": [rule.to_dict() for rule in rules],
        "ranked_rows": _records(scored),
        "trajectory_scope": TRAJECTORY_SCOPE,
        "trajectory_live_deployable": False,
        "trajectory_lookback_trading_days": int(trajectory_lookback),
        "trajectory_expected_rows": int(len(scored) * (trajectory_lookback + 1)),
        "trajectory_row_count": int(len(trajectory_frame)),
        "trajectory_complete_score_rows": int(
            trajectory_frame.get("shadow_strength_complete", pd.Series(dtype=bool))
            .fillna(False)
            .astype(bool)
            .sum()
        ),
        "trajectory_complete_history_stocks": complete_history_stocks,
        "trajectory_observations": _records(trajectory_frame),
        "trajectory_note": (
            "D-10 through D is reconstructed only for stocks confirmed on D; each row "
            "uses component sources strictly before its observation date. Historical "
            "cross-sectional rank is withheld because the universe is future-conditioned."
        ),
        "risk_state": (
            "high_risk_breakdown"
            if market.get("market_state") == "MARKET_HIGH_RISK_BREAKDOWN"
            else "shadow_observation"
        ),
        "action": "watch_only",
        "no_lookahead": "all score component source dates are strictly before as_of",
        "corporate_action_note": (
            "daily ranking does not use a forward return label; future corporate-action "
            "adjustment remains evaluator-only"
        ),
        "cost_slippage_liquidity_note": (
            "not an execution backtest; no order, position, cost, or slippage is applied"
        ),
        "mode": "shadow_observation_only",
        "formal_champion_changed": False,
        "formal_trade_effect": False,
        "promotion_decision": "blocked_before_promotion_review",
    }


def render_markdown(summary: dict[str, Any]) -> str:
    if summary["market_state"] == "MARKET_HIGH_RISK_BREAKDOWN":
        action_reason = "市場風險 gate 未解除，全部 `watch_only`。"
    else:
        action_reason = "分數尚未通過正式 promotion review，全部 `watch_only`。"
    lines = [
        f"# {summary['as_of']} Zhu Walkline 四項影子強度",
        "",
        f"- 大盤：`{summary['market_state']}`；多方 {summary['market_score']}；"
        f"風險 {summary['market_risk_score']}。",
        f"- 同日新鮮 KD 確認：{summary['candidate_rows']}；四項完整："
        f"{summary['complete_score_rows']}。",
        f"- 分數只作 shadow 排序；{action_reason}",
        "",
        "| 排名 | 股票 | 收盤 | 強度 | 主力proxy | 上影次數 | 量比 | 融資5日變化 | 通過項目 |",
        "|---:|---|---:|---:|---:|---:|---:|---:|---|",
    ]
    for row in summary["ranked_rows"]:
        rank = _num(row.get("shadow_strength_rank_within_signal_date"), 0)
        stock = f"{row.get('stock_id', '')} {row.get('stock_name', '')}".strip()
        passed_components = str(
            row.get("shadow_strength_passed_component_names", "")
        ).replace("|", ", ")
        lines.append(
            f"| {rank} | {stock} | {_num(row.get('close'), 2)} | "
            f"{_num(row.get('shadow_strength_score'), 0)} | "
            f"{_num(row.get('pre_main_force_net_lots_1d'), 2)} | "
            f"{_num(row.get('pre5_upper_tail_count'), 0)} | "
            f"{_num(row.get('pre_day_volume_ratio_20'), 4)} | "
            f"{_num(row.get('pre_margin_balance_change_5d_pct'), 4)}% | "
            f"{passed_components} |"
        )
    trajectory_rows = summary.get("trajectory_observations", [])
    lines.extend(
        [
            "",
            "## D-10～D 四項影子軌跡",
            "",
            "- 每列四項只使用嚴格早於該觀察日的資料。",
            "- 對象是 D 日確認後回看的股票；歷史橫斷面排名不顯示，"
            "不得解讀為當時已從全市場提早選出。",
            "- `trajectory_scope=retrospective_confirmed_candidates`；"
            "`trajectory_live_deployable=False`。",
        ]
    )
    if not trajectory_rows:
        lines.extend(["", "本日無可顯示的 D-10～D 軌跡。"])
    else:
        grouped: dict[tuple[str, str], list[dict[str, Any]]] = {}
        for row in trajectory_rows:
            key = (str(row.get("stock_id", "")), str(row.get("stock_name", "")))
            grouped.setdefault(key, []).append(row)
        for (stock_id, stock_name), rows in grouped.items():
            lines.extend(
                [
                    "",
                    f"### {stock_id} {stock_name}".rstrip(),
                    "",
                    "| 相對日 | 觀察日 | 最晚來源 | 強度 | 主力 | 上影次數 | 量比 | "
                    "融資5日變化 | 通過項目 |",
                    "|---|---|---|---:|---:|---:|---:|---:|---|",
                ]
            )
            ordered = sorted(rows, key=lambda item: int(item.get("lead_days", 0)), reverse=True)
            for row in ordered:
                passed = str(
                    row.get("shadow_strength_passed_component_names", "")
                ).replace("|", ", ")
                lines.append(
                    f"| {row.get('relative_day', '')} | {row.get('asof_date', '')} | "
                    f"{row.get('shadow_strength_feature_available_date', '') or ''} | "
                    f"{_num(row.get('shadow_strength_score'), 0)} | "
                    f"{_num(row.get('pre_main_force_net_lots_1d'), 2)} | "
                    f"{_num(row.get('pre5_upper_tail_count'), 0)} | "
                    f"{_num(row.get('pre_day_volume_ratio_20'), 4)} | "
                    f"{_num(row.get('pre_margin_balance_change_5d_pct'), 4)}% | "
                    f"{passed} |"
                )
    lines.extend(
        [
            "",
            "```text",
            "mode=shadow_observation_only",
            "formal_champion_changed=False",
            "formal_trade_effect=False",
            "action=watch_only",
            "promotion_decision=blocked_before_promotion_review",
            "```",
            "",
        ]
    )
    return "\n".join(lines)


def _empty_scored_frame(candidates: pd.DataFrame) -> pd.DataFrame:
    output = candidates.copy()
    output["shadow_strength_complete"] = pd.Series(dtype=bool)
    output["shadow_strength_score"] = pd.Series(dtype=float)
    output["shadow_strength_rank_within_signal_date"] = pd.Series(dtype=float)
    output["rise_score"] = pd.Series(dtype=float)
    return output


def _empty_trajectory_frame() -> pd.DataFrame:
    return pd.DataFrame({column: pd.Series(dtype=object) for column in TRAJECTORY_EXPORT_COLUMNS})


def _as_bool(values: pd.Series) -> pd.Series:
    if pd.api.types.is_bool_dtype(values):
        return values.fillna(False)
    return values.astype(str).str.lower().isin({"1", "true", "yes"})


def _safe_csv(frame: pd.DataFrame, path: Path) -> None:
    output = frame.copy()
    for column in output.select_dtypes(include=["object", "string"]).columns:
        output[column] = output[column].fillna("")
    output.to_csv(path, index=False, encoding="utf-8-sig", na_rep="")


def _records(frame: pd.DataFrame) -> list[dict[str, Any]]:
    return _json_safe(frame.to_dict(orient="records"))


def _json_safe(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set, np.ndarray)):
        return [_json_safe(item) for item in value]
    if isinstance(value, (pd.Timestamp, Path)):
        return str(value)
    if isinstance(value, (np.bool_, bool)):
        return bool(value)
    if isinstance(value, np.integer):
        return int(value)
    if isinstance(value, (np.floating, float)):
        return float(value) if np.isfinite(value) else None
    missing = pd.isna(value)
    if isinstance(missing, (bool, np.bool_)) and bool(missing):
        return None
    return value


def _num(value: Any, decimals: int) -> str:
    number = pd.to_numeric(pd.Series([value]), errors="coerce").iloc[0]
    return f"{float(number):.{decimals}f}" if pd.notna(number) else ""


def _repo_path(value: str) -> Path:
    path = Path(value)
    return path if path.is_absolute() else REPO_ROOT / path


def _load_yaml(path: Path) -> dict[str, Any]:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--asof", required=True)
    parser.add_argument("--config", default="config/zhu_walkline_shadow.yaml")
    parser.add_argument("--scanner-dir", default="reports/zhu_walkline_shadow")
    parser.add_argument("--output-dir", default=None)
    parser.add_argument(
        "--rules-csv",
        default="config/zhu_walkline_shadow_strength_rules.csv",
    )
    return parser.parse_args(argv)


if __name__ == "__main__":
    raise SystemExit(main())
