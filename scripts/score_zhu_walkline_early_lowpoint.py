"""Score a daily full-market D-5/D-3/D-1 early-lowpoint shadow watchlist."""

from __future__ import annotations

import argparse
from dataclasses import asdict
import json
from pathlib import Path
import shutil
import sqlite3
import sys
from typing import Any, Sequence

import numpy as np
import pandas as pd
import yaml


REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
for path in (REPO_ROOT, SRC_ROOT):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from abc_quant.features.early_observation_score import (  # noqa: E402
    EarlyObservationScoreConfig,
    score_early_observation,
)
from abc_quant.features.walkline_features import (  # noqa: E402
    compute_walkline_feature_history,
)
from abc_quant.validation.pit_grouping import (  # noqa: E402
    INSUFFICIENT_DATA,
    INSUFFICIENT_FEATURES,
    attach_cross_sectional_size_and_liquidity,
    attach_market_regime,
    attach_score_percentiles,
)


MODE = "shadow_observation_only"
STAGE_PRIORITY = {"D5_SETUP": 1, "D3_EARLY_TURN": 2, "D1_EARLY_OBSERVATION": 3}
FORBIDDEN_OUTPUT_TOKENS = (
    "future",
    "forward",
    "target",
    "d5_net_return",
    "d5_adjusted_return",
    "d5_close_date",
    "return_d5",
    "realized",
    "evaluator",
    "outcome",
    "label_",
    "actual_",
    "d5_group",
    "exit_",
    "net_return",
    "horizon",
)
BASE_OUTPUT_COLUMNS = (
    "asof_date",
    "observation_date",
    "stock_id",
    "early_observation_stage",
    "early_score",
    "core_score",
    "context_score",
    "eligibility",
    "confirmation_status",
    "d5_source_date",
    "d3_source_date",
    "d1_source_date",
    "close",
    "return_5d_pct",
    "distance_from_trailing_5d_low_pct",
    "d5_volume_ratio_20",
    "d5_volume_ratio_slope",
    "d5_ma20_slope_pct",
    "d5_pre5_min_abs_open_close_pct",
    "d5_lower_shadow_pct",
    "d5_lower_shadow_body_ratio",
    "d5_close_location_in_bar",
    "volume_ratio_20",
    "ma20_slope_pct",
    "pre5_min_abs_open_close_pct",
    "lower_shadow_pct",
    "lower_shadow_body_ratio",
    "close_location_in_bar",
    "avg_turnover_20_twd",
    "d5_selling_pressure_reason",
    "d5_tight_body_reason",
    "d5_lower_shadow_reason",
    "d5_tight_body_points",
    "d5_lower_shadow_points",
    "tight_body_contextual_only",
    "lower_shadow_contextual_only",
    "avoid_chase",
    "avoid_chase_trigger_return_5d",
    "avoid_chase_trigger_distance",
    "avoid_chase_reason",
    "risk_state",
    "action",
    "components_json",
    "mode",
    "formal_trade_effect",
)
CONTEXT_OUTPUT_COLUMNS = (
    "sector",
    "market_percentile",
    "sector_within_percentile",
    "free_float_market_cap",
    "size_percentile",
    "size_tier",
    "liquidity_percentile",
    "liquidity_tier",
    "market_trend",
    "market_volatility",
    "market_regime",
    "concept_status",
    "size_status",
    "paid_in_capital_fallback_used",
    "shadow_strength_score",
    "shadow_strength_tier",
    "shadow_strength_score_status",
    "shadow_strength_source_scope",
)
LIVE_OUTPUT_COLUMNS = (*BASE_OUTPUT_COLUMNS, *CONTEXT_OUTPUT_COLUMNS)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    config = _load_yaml(_repo_path(args.config))
    early_config = config.get("early_lowpoint_report", {})
    if not isinstance(early_config, dict) or not early_config.get("enabled", True):
        print("early_lowpoint_report_enabled=False")
        return 0
    sqlite_path = Path(config["data"]["sqlite_path"])
    asof_date = resolve_asof_date(sqlite_path, args.asof)
    body_window = int(early_config.get("trailing_body_window", 5))
    if body_window != 5:
        raise ValueError("early lowpoint prior-body window is fixed at five trading days")
    score_config = build_score_config(early_config)
    minimum_core_score = float(
        early_config.get("minimum_core_score_to_report", 30.0)
    )
    prices = load_adjusted_history(
        sqlite_path,
        asof_date=asof_date,
        lookback_calendar_days=max(
            120, int(early_config.get("lookback_trading_days", 60)) * 3
        ),
    )
    market_calendar = load_market_calendar(
        sqlite_path,
        start_date=pd.Timestamp(prices["date"].min()).date().isoformat(),
        end_date=asof_date,
    )
    history = build_early_feature_history(
        prices,
        asof_date=asof_date,
        trailing_body_window=body_window,
    )
    rows = build_daily_early_watchlist(
        history,
        asof_date=asof_date,
        market_calendar=market_calendar,
        score_config=score_config,
        minimum_core_score=minimum_core_score,
        avoid_chase_return_5d_pct=float(
            early_config.get("avoid_chase_return_5d_pct", 8.0)
        ),
        maximum_distance_from_low_pct=float(
            early_config.get("maximum_distance_from_trailing_5d_low_pct", 8.0)
        ),
    )
    rows = attach_daily_context(
        rows,
        history=history,
        sqlite_path=sqlite_path,
        asof_date=asof_date,
        volatility_high_threshold=float(
            early_config.get("market_volatility_high_threshold_pct", 2.56)
        ),
    )
    rows = attach_four_component_context(
        rows,
        scanner_dir=_repo_path(args.scanner_dir),
        asof_date=asof_date,
    )
    rows = ensure_live_output_schema(rows)
    assert_live_output_contract(rows)
    output_dir = _repo_path(args.output_dir or args.scanner_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    paths = write_outputs(
        rows,
        output_dir=output_dir,
        asof_date=asof_date,
        config=early_config,
        score_config=score_config,
        body_window=body_window,
        minimum_core_score=minimum_core_score,
    )
    print(f"asof_date={asof_date}")
    print(f"early_lowpoint_rows={len(rows)}")
    print("mode=shadow_observation_only")
    print("formal_champion_changed=False")
    print("formal_trade_effect=False")
    print(f"csv={paths['csv']}")
    print(f"markdown={paths['markdown']}")
    return 0


def resolve_asof_date(sqlite_path: Path, requested: str) -> str:
    with sqlite3.connect(sqlite_path) as connection:
        if requested == "latest":
            row = connection.execute(
                "select max(date) from tw_adjusted_ohlcv_daily"
            ).fetchone()
        else:
            row = connection.execute(
                "select max(date) from tw_adjusted_ohlcv_daily where date <= ?",
                [requested],
            ).fetchone()
    if row is None or not row[0]:
        raise ValueError(f"no adjusted market date available for {requested}")
    return pd.Timestamp(row[0]).date().isoformat()


def load_adjusted_history(
    sqlite_path: Path,
    *,
    asof_date: str,
    lookback_calendar_days: int,
) -> pd.DataFrame:
    start_date = (
        pd.Timestamp(asof_date) - pd.Timedelta(days=lookback_calendar_days)
    ).date().isoformat()
    query = """
        select date, stock_id,
               coalesce(adj_open, open) as open,
               coalesce(adj_high, high) as high,
               coalesce(adj_low, low) as low,
               coalesce(adj_close, close) as close,
               volume
        from tw_adjusted_ohlcv_daily as price
        where date between ? and ? and length(stock_id) = 4
          and exists (
              select 1
              from stock_pit_sector_membership_daily as membership
              where membership.date = ?
                and membership.stock_id = price.stock_id
                and membership.collection_layer = 'sector'
                and membership.membership_mode = 'point_in_time_observed_asof'
          )
        order by stock_id, date
    """
    with sqlite3.connect(sqlite_path) as connection:
        frame = pd.read_sql_query(
            query,
            connection,
            params=[start_date, asof_date, asof_date],
            parse_dates=["date"],
        )
    if frame.empty:
        raise ValueError("adjusted price history is empty")
    frame["stock_id"] = frame["stock_id"].astype(str).str.zfill(4)
    if frame.duplicated(["date", "stock_id"]).any():
        raise ValueError("adjusted price history contains duplicate stock dates")
    return frame


def load_market_calendar(
    sqlite_path: Path, *, start_date: str, end_date: str
) -> pd.DatetimeIndex:
    query = "select distinct date from {table} where date between ? and ?"
    calendars: dict[str, set[pd.Timestamp]] = {}
    with sqlite3.connect(sqlite_path) as connection:
        for table in ("tw_adjusted_ohlcv_daily", "daily_ohlcv_features"):
            values = pd.read_sql_query(
                query.format(table=table),
                connection,
                params=[start_date, end_date],
                parse_dates=["date"],
            )
            calendars[table] = set(pd.to_datetime(values["date"], errors="raise"))
    if not calendars["tw_adjusted_ohlcv_daily"]:
        raise ValueError("market calendar is empty")
    if calendars["tw_adjusted_ohlcv_daily"] != calendars["daily_ohlcv_features"]:
        raise ValueError("market calendar sources disagree")
    return pd.DatetimeIndex(sorted(calendars["tw_adjusted_ohlcv_daily"]))


def build_early_feature_history(
    adjusted_prices: pd.DataFrame,
    *,
    asof_date: str,
    trailing_body_window: int = 5,
) -> pd.DataFrame:
    if trailing_body_window != 5:
        raise ValueError("pre5 body feature requires exactly five prior sessions")
    price_columns = ["date", "stock_id", "open", "high", "low", "close", "volume"]
    features = compute_walkline_feature_history(
        adjusted_prices[price_columns], asof_date=asof_date
    ).sort_values(["stock_id", "date"])
    grouped = features.groupby("stock_id", sort=False, group_keys=False)
    features["daily_return_pct"] = pd.to_numeric(
        features["return_1d"], errors="coerce"
    ) * 100.0
    features["return_5d_pct"] = pd.to_numeric(
        features["return_5d"], errors="coerce"
    ) * 100.0
    features["return_20d_pct"] = pd.to_numeric(
        features["return_20d"], errors="coerce"
    ) * 100.0
    features["ma20_slope_pct"] = grouped["ma20"].pct_change(3) / 3.0 * 100.0
    features["volume_ratio_20"] = pd.to_numeric(
        features["vol_ratio_20"], errors="coerce"
    )
    features["volume_ratio_slope"] = grouped["volume_ratio_20"].diff(2) / 2.0
    features["volume_slope_acceleration"] = grouped["volume_ratio_slope"].diff()
    features["close_to_ma20_pct"] = (
        pd.to_numeric(features["close"], errors="coerce")
        / pd.to_numeric(features["ma20"], errors="coerce")
        - 1.0
    ) * 100.0
    body_fraction = pd.to_numeric(features["k_body_pct"], errors="coerce").abs()
    upper_fraction = pd.to_numeric(features["upper_shadow_pct"], errors="coerce")
    lower_fraction = pd.to_numeric(features["lower_shadow_pct"], errors="coerce")
    safe_body = body_fraction.where(body_fraction.gt(1e-9))
    features["upper_shadow_body_ratio"] = upper_fraction.div(safe_body)
    features["lower_shadow_body_ratio"] = lower_fraction.div(safe_body)
    features["lower_shadow_pct"] = lower_fraction * 100.0
    features["close_location_in_bar"] = pd.to_numeric(
        features["close_position_in_range"], errors="coerce"
    )
    body_pct = pd.to_numeric(
        features["kd_open_close_body_pct"], errors="coerce"
    ).abs() * 100.0
    prior_body_pct = body_pct.groupby(features["stock_id"]).shift(1)
    features["pre5_min_abs_open_close_pct"] = (
        prior_body_pct.groupby(features["stock_id"])
        .rolling(trailing_body_window, min_periods=trailing_body_window)
        .min()
        .reset_index(level=0, drop=True)
    )
    features["kd_k_change_1d"] = pd.to_numeric(
        features["kd_k9"], errors="coerce"
    ) - pd.to_numeric(features["kd_prev_k9"], errors="coerce")
    features["price_stabilized"] = (
        features["daily_return_pct"].ge(0.0)
        & ~features["lower_low"].fillna(False).astype(bool)
    )
    features["consecutive_down_days"] = grouped["daily_return_pct"].transform(
        _consecutive_negative_counts
    )
    features["volume_spike_selloff"] = (
        features["volume_ratio_20"].gt(1.5)
        & features["daily_return_pct"].lt(0.0)
    )
    features["avg_turnover_20_twd"] = pd.to_numeric(
        features["amount_ma20"], errors="coerce"
    )
    trailing_low = (
        pd.to_numeric(features["low"], errors="coerce")
        .groupby(features["stock_id"])
        .rolling(5, min_periods=5)
        .min()
        .reset_index(level=0, drop=True)
    )
    features["distance_from_trailing_5d_low_pct"] = (
        pd.to_numeric(features["close"], errors="coerce") / trailing_low - 1.0
    ) * 100.0
    features["volatility_20d_pct"] = (
        pd.to_numeric(features["return_1d"], errors="coerce")
        .groupby(features["stock_id"])
        .rolling(20, min_periods=20)
        .std(ddof=0)
        .reset_index(level=0, drop=True)
        * 100.0
    )
    return features


def build_score_config(config: dict[str, Any]) -> EarlyObservationScoreConfig:
    return EarlyObservationScoreConfig(
        max_volume_ratio_20=float(config.get("max_volume_ratio_20", 0.50)),
        min_ma20_slope_pct=float(
            config.get("minimum_ma20_slope_pct_per_day", 0.0)
        ),
        max_tight_body_pct=float(config.get("max_abs_open_close_pct", 1.2)),
        max_volume_ratio_slope=float(
            config.get("maximum_volume_ratio_slope", 0.0)
        ),
        min_pullback_return_pct=float(
            config.get("minimum_pullback_return_pct", -4.0)
        ),
        max_pullback_return_pct=float(
            config.get("maximum_pullback_return_pct", 0.5)
        ),
        max_upper_shadow_body_ratio=float(
            config.get("maximum_upper_shadow_to_body_ratio", 1.0)
        ),
        max_consecutive_down_days=int(
            config.get("maximum_consecutive_down_days", 2)
        ),
        min_lower_shadow_body_ratio=float(
            config.get("minimum_lower_shadow_to_body_ratio", 1.0)
        ),
        min_lower_shadow_pct=float(config.get("minimum_lower_shadow_pct", 1.0)),
        min_close_location_in_bar=float(
            config.get("minimum_close_location_in_bar", 0.60)
        ),
        max_lower_shadow_volume_ratio=float(
            config.get("maximum_lower_shadow_volume_ratio", 1.50)
        ),
    )


def build_daily_early_watchlist(
    history: pd.DataFrame,
    *,
    asof_date: str,
    market_calendar: Sequence[Any] | pd.DatetimeIndex,
    score_config: EarlyObservationScoreConfig,
    minimum_core_score: float,
    avoid_chase_return_5d_pct: float,
    maximum_distance_from_low_pct: float,
) -> pd.DataFrame:
    records: list[dict[str, Any]] = []
    asof = pd.Timestamp(asof_date)
    calendar = pd.DatetimeIndex(
        pd.to_datetime(pd.Index(market_calendar), errors="raise")
    ).drop_duplicates().sort_values()
    if calendar.empty:
        raise ValueError("explicit market calendar must not be empty")
    asof_positions = np.flatnonzero(calendar == asof)
    if len(asof_positions) != 1:
        raise ValueError("as-of date must appear exactly once in the market calendar")
    asof_position = int(asof_positions[0])
    for stock_id, stock_rows in history.groupby("stock_id", sort=False):
        ordered = stock_rows.sort_values("date").reset_index(drop=True)
        ordered["date"] = pd.to_datetime(ordered["date"], errors="raise")
        if ordered["date"].duplicated().any():
            raise ValueError(f"duplicate history dates for stock {stock_id}")
        by_date = ordered.set_index("date", drop=False)
        if asof not in by_date.index:
            continue
        candidates: list[
            tuple[int, Any, dict[str, pd.Series], float, float]
        ] = []
        stage_specs = (
            ({"D-5": 0}),
            ({"D-5": -2, "D-3": 0}),
            ({"D-5": -4, "D-3": -2, "D-1": 0}),
        )
        for offsets in stage_specs:
            if any(asof_position + offset < 0 for offset in offsets.values()):
                continue
            stage_dates = {
                stage: calendar[asof_position + offset]
                for stage, offset in offsets.items()
            }
            if any(stage_date not in by_date.index for stage_date in stage_dates.values()):
                continue
            stages = {stage: by_date.loc[stage_date] for stage, stage_date in stage_dates.items()}
            result = score_early_observation(stages, config=score_config)
            core_score = sum(
                component.points
                for component in result.components
                if component.evidence_status == "core"
            )
            context_score = sum(
                component.points
                for component in result.components
                if component.evidence_status == "unstable_context_only"
            )
            if (
                result.eligibility == "SHADOW_WATCH_ELIGIBLE"
                and result.early_score is not None
                and core_score >= minimum_core_score
            ):
                candidates.append(
                    (
                        STAGE_PRIORITY[result.stage],
                        result,
                        stages,
                        core_score,
                        context_score,
                    )
                )
        if not candidates:
            continue
        _priority, result, stages, core_score, context_score = max(
            candidates,
            key=lambda item: (item[0], item[1].early_score or 0.0),
        )
        current = by_date.loc[asof]
        d5_row = stages["D-5"]
        component_map = {component.name: component for component in result.components}
        return_5d = _number(current.get("return_5d_pct"))
        distance_from_low = _number(
            current.get("distance_from_trailing_5d_low_pct")
        )
        return_trigger = bool(
            return_5d is not None
            and return_5d >= avoid_chase_return_5d_pct
        )
        distance_trigger = bool(
            distance_from_low is not None
            and distance_from_low > maximum_distance_from_low_pct
        )
        avoid_chase = return_trigger or distance_trigger
        tight_body_component = component_map.get("tight_body_compression")
        lower_shadow_component = component_map.get(
            "bullish_lower_shadow_support"
        )
        records.append(
            {
                "asof_date": asof_date,
                "observation_date": asof,
                "stock_id": str(stock_id).zfill(4),
                "early_observation_stage": result.stage,
                "early_score": result.early_score,
                "core_score": core_score,
                "context_score": context_score,
                "eligibility": result.eligibility,
                "confirmation_status": result.confirmation_status,
                "d5_source_date": pd.Timestamp(stages["D-5"]["date"])
                .date()
                .isoformat(),
                "d3_source_date": _stage_date(stages, "D-3"),
                "d1_source_date": _stage_date(stages, "D-1"),
                "close": _number(current.get("close")),
                "return_5d_pct": return_5d,
                "distance_from_trailing_5d_low_pct": distance_from_low,
                "d5_volume_ratio_20": _number(d5_row.get("volume_ratio_20")),
                "d5_volume_ratio_slope": _number(
                    d5_row.get("volume_ratio_slope")
                ),
                "d5_ma20_slope_pct": _number(d5_row.get("ma20_slope_pct")),
                "d5_pre5_min_abs_open_close_pct": _number(
                    d5_row.get("pre5_min_abs_open_close_pct")
                ),
                "d5_lower_shadow_pct": _number(d5_row.get("lower_shadow_pct")),
                "d5_lower_shadow_body_ratio": _number(
                    d5_row.get("lower_shadow_body_ratio")
                ),
                "d5_close_location_in_bar": _number(
                    d5_row.get("close_location_in_bar")
                ),
                "volume_ratio_20": _number(current.get("volume_ratio_20")),
                "ma20_slope_pct": _number(current.get("ma20_slope_pct")),
                "pre5_min_abs_open_close_pct": _number(
                    current.get("pre5_min_abs_open_close_pct")
                ),
                "lower_shadow_pct": _number(current.get("lower_shadow_pct")),
                "lower_shadow_body_ratio": _number(
                    current.get("lower_shadow_body_ratio")
                ),
                "close_location_in_bar": _number(
                    current.get("close_location_in_bar")
                ),
                "avg_turnover_20_twd": _number(
                    current.get("avg_turnover_20_twd")
                ),
                "d5_selling_pressure_reason": _component_reason(
                    component_map, "selling_pressure_contraction"
                ),
                "d5_tight_body_reason": _component_reason(
                    component_map, "tight_body_compression"
                ),
                "d5_lower_shadow_reason": _component_reason(
                    component_map, "bullish_lower_shadow_support"
                ),
                "d5_tight_body_points": (
                    tight_body_component.points
                    if tight_body_component is not None
                    else 0.0
                ),
                "d5_lower_shadow_points": (
                    lower_shadow_component.points
                    if lower_shadow_component is not None
                    else 0.0
                ),
                "tight_body_contextual_only": True,
                "lower_shadow_contextual_only": True,
                "avoid_chase": avoid_chase,
                "avoid_chase_trigger_return_5d": return_trigger,
                "avoid_chase_trigger_distance": distance_trigger,
                "avoid_chase_reason": _avoid_chase_reason(
                    return_trigger=return_trigger,
                    distance_trigger=distance_trigger,
                ),
                "risk_state": "avoid_chase" if avoid_chase else "early_shadow_watch",
                "action": "avoid_chase" if avoid_chase else "watch_only",
                "components_json": json.dumps(
                    [component.to_dict() for component in result.components],
                    ensure_ascii=False,
                    separators=(",", ":"),
                ),
                "mode": MODE,
                "formal_trade_effect": False,
            }
        )
    if not records:
        return pd.DataFrame(columns=BASE_OUTPUT_COLUMNS)
    output = pd.DataFrame(records).reindex(columns=BASE_OUTPUT_COLUMNS)
    return output.sort_values(
        ["avoid_chase", "core_score", "context_score", "stock_id"],
        ascending=[True, False, False, True],
    ).reset_index(drop=True)


def attach_daily_context(
    rows: pd.DataFrame,
    *,
    history: pd.DataFrame,
    sqlite_path: Path,
    asof_date: str,
    volatility_high_threshold: float,
) -> pd.DataFrame:
    if rows.empty:
        return rows
    sector = load_sector_asof(sqlite_path, asof_date=asof_date)
    output = rows.merge(sector, on="stock_id", how="left", validate="one_to_one")
    output["sector"] = output["sector"].fillna(INSUFFICIENT_FEATURES)
    output = attach_score_percentiles(
        output,
        score_column="early_score",
        date_column="observation_date",
        sector_column="sector",
    )
    output["free_float_market_cap"] = np.nan
    output = attach_cross_sectional_size_and_liquidity(
        output,
        date_column="observation_date",
        free_float_market_cap_column="free_float_market_cap",
        liquidity_column="avg_turnover_20_twd",
    )
    current = history[pd.to_datetime(history["date"]).eq(pd.Timestamp(asof_date))]
    market_return = pd.to_numeric(current["return_20d_pct"], errors="coerce").median()
    market_volatility = pd.to_numeric(
        current["volatility_20d_pct"], errors="coerce"
    ).median()
    trend = "up" if market_return > 2.0 else "down" if market_return < -2.0 else "flat"
    volatility = "high" if market_volatility >= volatility_high_threshold else "low"
    output["market_trend"] = trend
    output["market_volatility"] = volatility
    output = attach_market_regime(output)
    output["concept_status"] = INSUFFICIENT_DATA
    output["size_status"] = INSUFFICIENT_FEATURES
    output["paid_in_capital_fallback_used"] = False
    return output


def load_sector_asof(sqlite_path: Path, *, asof_date: str) -> pd.DataFrame:
    query = """
        select stock_id, collection_name as sector, pit_quality_rank
        from stock_pit_sector_membership_daily
        where date = ? and collection_layer = 'sector'
          and membership_mode = 'point_in_time_observed_asof'
        order by stock_id, pit_quality_rank
    """
    with sqlite3.connect(sqlite_path) as connection:
        frame = pd.read_sql_query(query, connection, params=[asof_date])
    if frame.empty:
        return pd.DataFrame(columns=["stock_id", "sector"])
    frame["stock_id"] = frame["stock_id"].astype(str).str.zfill(4)
    return frame.drop_duplicates("stock_id", keep="first")[["stock_id", "sector"]]


def attach_four_component_context(
    rows: pd.DataFrame, *, scanner_dir: Path, asof_date: str
) -> pd.DataFrame:
    del scanner_dir, asof_date
    if rows.empty:
        return rows
    output = rows.copy()
    output["shadow_strength_score"] = np.nan
    output["shadow_strength_tier"] = "SEPARATE_CONFIRMED_REPORT_ONLY"
    output["shadow_strength_score_status"] = "NOT_APPLICABLE_EARLY_STAGE"
    output["shadow_strength_source_scope"] = "separate_confirmed_report_only"
    return output


def ensure_live_output_schema(rows: pd.DataFrame) -> pd.DataFrame:
    output = rows.copy()
    unexpected = sorted(set(output.columns).difference(LIVE_OUTPUT_COLUMNS))
    if unexpected:
        raise ValueError(f"unexpected early watchlist columns: {unexpected}")
    for column in LIVE_OUTPUT_COLUMNS:
        if column not in output:
            output[column] = pd.Series(index=output.index, dtype="object")
    return output.reindex(columns=LIVE_OUTPUT_COLUMNS)


def assert_live_output_contract(rows: pd.DataFrame) -> None:
    required = {
        "asof_date",
        "observation_date",
        "stock_id",
        "eligibility",
        "early_score",
        "action",
        "mode",
        "formal_trade_effect",
    }
    missing = required.difference(rows.columns)
    if missing:
        raise ValueError(f"early watchlist schema missing columns: {sorted(missing)}")
    forbidden = [
        column
        for column in rows.columns
        if any(token in column.lower() for token in FORBIDDEN_OUTPUT_TOKENS)
    ]
    if forbidden:
        raise ValueError(f"early watchlist contains evaluator columns: {forbidden}")
    if "mode" in rows and not rows["mode"].astype(str).eq(MODE).all():
        raise ValueError("early watchlist must remain shadow_observation_only")
    if "formal_trade_effect" in rows and rows["formal_trade_effect"].astype(bool).any():
        raise ValueError("early watchlist cannot have formal trade effect")


def write_outputs(
    rows: pd.DataFrame,
    *,
    output_dir: Path,
    asof_date: str,
    config: dict[str, Any],
    score_config: EarlyObservationScoreConfig,
    body_window: int,
    minimum_core_score: float,
) -> dict[str, Path]:
    dated_base = output_dir / f"{asof_date}_zhu_walkline_early_lowpoint"
    paths = {
        "csv": dated_base.with_suffix(".csv"),
        "json": dated_base.with_suffix(".json"),
        "markdown": dated_base.with_suffix(".md"),
    }
    rows.to_csv(paths["csv"], index=False, encoding="utf-8-sig")
    stage_counts = (
        rows.get("early_observation_stage", pd.Series(dtype=str))
        .value_counts()
        .to_dict()
    )
    summary = {
        "as_of": asof_date,
        "mode": MODE,
        "formal_champion_changed": False,
        "formal_trade_effect": False,
        "default_action": "watch_only",
        "candidate_rows": len(rows),
        "universe": "pit_sector_classified_equities",
        "avoid_chase_rows": int(rows.get("avoid_chase", pd.Series(dtype=bool)).sum()),
        "stage_counts": stage_counts,
        "action_counts": (
            rows.get("action", pd.Series(dtype=str)).value_counts().to_dict()
        ),
        "core_factor": "volume_contraction_with_positive_ma20_slope",
        "tight_body_evidence_status": "unstable_context_only",
        "lower_shadow_evidence_status": "unstable_context_only",
        "concept_status": INSUFFICIENT_DATA,
        "size_status": INSUFFICIENT_FEATURES,
        "thresholds": {
            **asdict(score_config),
            "trailing_body_window": body_window,
            "minimum_core_score_to_report": minimum_core_score,
            "avoid_chase_return_5d_pct": float(
                config.get("avoid_chase_return_5d_pct", 8.0)
            ),
            "maximum_distance_from_trailing_5d_low_pct": float(
                config.get("maximum_distance_from_trailing_5d_low_pct", 8.0)
            ),
        },
        "four_component_strength_scope": "separate_confirmed_report_only",
    }
    paths["json"].write_text(
        json.dumps(_json_safe(summary), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    paths["markdown"].write_text(
        render_markdown(summary, rows), encoding="utf-8"
    )
    for suffix, key in (("csv", "csv"), ("json", "json"), ("md", "markdown")):
        latest = output_dir / f"latest_zhu_walkline_early_lowpoint.{suffix}"
        shutil.copyfile(paths[key], latest)
        paths[f"latest_{key}"] = latest
    return paths


def render_markdown(summary: dict[str, Any], rows: pd.DataFrame) -> str:
    columns = [
        "stock_id",
        "early_observation_stage",
        "early_score",
        "core_score",
        "d5_tight_body_points",
        "d5_lower_shadow_points",
        "context_score",
        "d5_volume_ratio_20",
        "d5_pre5_min_abs_open_close_pct",
        "d5_lower_shadow_reason_zh",
        "sector",
        "risk_state",
        "action",
    ]
    display = rows.copy()
    display["d5_lower_shadow_reason_zh"] = display.get(
        "d5_lower_shadow_reason", pd.Series(index=display.index, dtype=str)
    ).map(
        {
            "bullish_lower_shadow_support": "下影承接加分",
            "lower_shadow_risk": "下影型態有風險，不加分",
            "lower_shadow_unconfirmed": "下影承接未確認",
        }
    )
    present = [column for column in columns if column in display.columns]
    avoid_columns = [
        "stock_id",
        "return_5d_pct",
        "distance_from_trailing_5d_low_pct",
        "avoid_chase_reason",
    ]
    avoid_rows = display[display["avoid_chase"].fillna(False).astype(bool)]
    lines = [
        f"# Zhu Walkline 提早低點觀察 — {summary['as_of']}",
        "",
        "- 核心資格：月線斜率為正，D-5 量比 `<=0.50`，且為有限回檔、無長上影／持續破底。",
        "- 母體只含該日具有 point-in-time 產業身分的個股；ETF 等非個股商品排除。",
        "- 開收差 `<=1.2%` 與下影承接各只作 5 分情境加分，跨期證據不穩定。",
        "- 入池門檻只看 core score；調高門檻也不會讓小實體或下影線變成隱性硬條件。",
        "- 主要排序為 core score，再用情境分處理同分；表格只顯示前 50 筆。",
        "- 階段圖例：D-5=縮量正趨勢起始、D-3=止跌/K轉向、D-1=站回月線且價量增強；不是訊號後第 1 日，也不保證隔日確認。",
        "- `d5_` 欄位來自該早期來源日；無前綴欄位才是目前觀察日。",
        "- 四項影子強度（主力、無上影、量比、融資 5 日變化）仍是確認名單主排序；提早池不反向合併確認後分數。",
        "- 這是全市場 D-5／D-3／D-1 影子觀察，不是買進指令。",
        f"- 候選共 {summary['candidate_rows']}：watch_only {summary['action_counts'].get('watch_only', 0)}、avoid_chase {summary['action_counts'].get('avoid_chase', 0)}。",
        "- avoid_chase：近 5 日漲幅至少 8%，或距近 5 日低點超過 8%。",
        "",
        _markdown_table(display[present].head(50)),
        "",
        "## Avoid-chase 風險列",
        "",
        _markdown_table(avoid_rows[avoid_columns]),
        "",
        "```text",
        "mode=shadow_observation_only",
        "formal_champion_changed=False",
        "formal_trade_effect=False",
        "default_action=watch_only",
        "row_actions=watch_only|avoid_chase",
        "```",
    ]
    return "\n".join(lines) + "\n"


def _consecutive_negative_counts(values: pd.Series) -> pd.Series:
    count = 0
    output: list[int] = []
    for value in pd.to_numeric(values, errors="coerce"):
        count = count + 1 if np.isfinite(value) and value < 0 else 0
        output.append(count)
    return pd.Series(output, index=values.index, dtype=int)


def _stage_date(stages: dict[str, pd.Series], stage: str) -> str:
    if stage not in stages:
        return ""
    return pd.Timestamp(stages[stage]["date"]).date().isoformat()


def _component_reason(component_map: dict[str, Any], name: str) -> str:
    component = component_map.get(name)
    return str(component.reason) if component is not None else "not_evaluated"


def _avoid_chase_reason(*, return_trigger: bool, distance_trigger: bool) -> str:
    if return_trigger and distance_trigger:
        return "return_5d_and_distance_from_low"
    if return_trigger:
        return "return_5d_extended"
    if distance_trigger:
        return "distance_from_low_extended"
    return "not_triggered"


def _number(value: Any) -> float | None:
    try:
        output = float(value)
    except (TypeError, ValueError):
        return None
    return output if np.isfinite(output) else None


def _markdown_table(frame: pd.DataFrame) -> str:
    if frame.empty:
        return "_No candidates._"
    columns = list(frame.columns)
    header = "| " + " | ".join(columns) + " |"
    separator = "|" + "|".join(["---"] * len(columns)) + "|"
    body = []
    for row in frame.itertuples(index=False, name=None):
        values = []
        for value in row:
            if isinstance(value, float):
                values.append("" if not np.isfinite(value) else f"{value:.4f}")
            else:
                values.append(str(value))
        body.append("| " + " | ".join(values) + " |")
    return "\n".join([header, separator, *body])


def _json_safe(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(item) for item in value]
    if isinstance(value, np.integer):
        return int(value)
    if isinstance(value, (np.floating, float)):
        return float(value) if np.isfinite(value) else None
    return value


def _repo_path(value: str | Path) -> Path:
    path = Path(value)
    return path if path.is_absolute() else REPO_ROOT / path


def _load_yaml(path: Path) -> dict[str, Any]:
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("shadow config must be a mapping")
    return payload


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--asof", default="latest")
    parser.add_argument("--config", default="config/zhu_walkline_shadow.yaml")
    parser.add_argument("--scanner-dir", default="reports/zhu_walkline_shadow")
    parser.add_argument("--output-dir", default=None)
    return parser.parse_args(argv)


if __name__ == "__main__":
    raise SystemExit(main())
