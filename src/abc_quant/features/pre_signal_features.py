"""Point-in-time features strictly before a signal date.

The helpers in this module are intentionally signal-agnostic.  They accept a
table of dated stock events plus local price, flow, holder, margin, or wide
panel histories and return one row per event.  Every source row is filtered by
``source_date < signal_date`` before a feature is calculated.
"""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any

import numpy as np
import pandas as pd


PERCENT_BOUNDARY_TOLERANCE = 1e-9


PRICE_FEATURES = [
    "pre_price_source_date",
    "pre_return_1d_pct",
    "pre_return_5d_pct",
    "pre_return_20d_pct",
    "pre_close_to_sma20_pct",
    "pre_range_pos_20",
    "pre_day_volume_ratio_20",
    "pre5_mean_day_volume_ratio_20",
    "pre5_max_day_volume_ratio_20",
    "pre5_min_abs_open_close_pct",
    "pre5_tight_body_count_le_1_2pct",
    "pre5_tight_body_exists_le_1_2pct",
    "pre5_mean_turnover_million_twd",
    "pre5_upper_tail_count",
    "pre5_volume_exhaustion_count",
    "pre5_late_chase_count",
]

INSTITUTIONAL_FEATURES = [
    "pre_institutional_source_date",
    "pre_foreign_net_shares_1d",
    "pre_foreign_net_shares_5d",
    "pre_foreign_net_volume_ratio_1d_pct",
    "pre_foreign_net_volume_ratio_5d_pct",
    "pre_trust_net_volume_ratio_5d_pct",
    "pre_dealer_net_volume_ratio_5d_pct",
    "pre_institutional_net_volume_ratio_5d_pct",
    "pre_foreign_positive_day_ratio_5d",
    "pre_institutional_positive_day_ratio_5d",
]

MAIN_FORCE_FEATURES = [
    "pre_main_force_source_date",
    "pre_main_force_net_lots_1d",
    "pre_main_force_net_lots_5d",
    "pre_main_force_net_volume_ratio_5d_pct",
    "pre_main_force_positive_day_ratio_5d",
    "pre_broker_count_source_date",
    "pre_broker_count_diff_1d",
    "pre_broker_count_diff_5d_sum",
]

HOLDER_FEATURES = [
    "pre_holder_source_date",
    "pre_holder_lag_days",
    "pre_big_holder_ratio_1000_lots_pct",
    "pre_big_holder_ratio_delta_1w_pctpt",
    "pre_big_holder_ratio_delta_4w_pctpt",
    "pre_big_holder_count_delta_1w",
    "pre_big_holder_count_delta_4w",
]

MARGIN_FEATURES = [
    "pre_margin_source_date",
    "pre_margin_available_date",
    "pre_margin_balance",
    "pre_margin_balance_change_5d_pct",
    "pre_margin_balance_change_20d_pct",
]

NUMERIC_PRE_SIGNAL_FEATURES = [
    column
    for column in (
        PRICE_FEATURES
        + INSTITUTIONAL_FEATURES
        + MAIN_FORCE_FEATURES
        + HOLDER_FEATURES
        + MARGIN_FEATURES
    )
    if not column.endswith("_date") and column != "pre5_tight_body_exists_le_1_2pct"
]


def build_pre_signal_feature_frame(
    signals: pd.DataFrame,
    *,
    market_calendar: Iterable[Any] | pd.DataFrame,
    price_history: pd.DataFrame,
    institutional_history: pd.DataFrame,
    holder_history: pd.DataFrame,
    margin_history: pd.DataFrame,
    main_force_panel: pd.DataFrame | None = None,
    broker_count_panel: pd.DataFrame | None = None,
) -> pd.DataFrame:
    """Return one feature row per signal using strictly earlier source rows."""
    events = _prepare_signals(signals)
    price = _prepare_long_history(price_history, date_column="date")
    institutional = _prepare_long_history(institutional_history, date_column="date")
    holder = _prepare_long_history(holder_history, date_column="date")
    margin = _prepare_long_history(margin_history, date_column="trade_date")
    main_force = _prepare_wide_panel(main_force_panel)
    broker_count = _prepare_wide_panel(broker_count_panel)

    price_groups = _group_by_stock(price)
    institutional_groups = _group_by_stock(institutional)
    holder_groups = _group_by_stock(holder)
    margin_groups = _group_by_stock(margin)
    market_dates = _prepare_market_calendar(market_calendar)

    records: list[dict[str, Any]] = []
    for event in events.itertuples(index=False):
        stock_id = str(event.stock_id)
        signal_date = pd.Timestamp(event.signal_date)
        expected_source_date = _expected_prior_market_date(market_dates, signal_date)
        price_pre = _strictly_before(price_groups.get(stock_id), signal_date, "date")
        institutional_pre = _strictly_before(
            institutional_groups.get(stock_id), signal_date, "date"
        )
        holder_pre = _strict_holder_history(holder_groups.get(stock_id), signal_date)
        margin_pre = _strict_margin_history(margin_groups.get(stock_id), signal_date)

        row: dict[str, Any] = {
            "asof_date": signal_date.strftime("%Y-%m-%d"),
            "stock_id": stock_id,
        }
        row.update(
            _price_features(
                price_pre,
                expected_source_date=expected_source_date,
            )
        )
        row.update(
            _institutional_features(
                institutional_pre,
                price_pre,
                expected_source_date=expected_source_date,
            )
        )
        row.update(
            _wide_flow_features(
                main_force,
                stock_id=stock_id,
                signal_date=signal_date,
                price_pre=price_pre,
                prefix="main_force",
                expected_source_date=expected_source_date,
            )
        )
        row.update(
            _wide_flow_features(
                broker_count,
                stock_id=stock_id,
                signal_date=signal_date,
                price_pre=price_pre,
                prefix="broker_count",
                expected_source_date=expected_source_date,
            )
        )
        row.update(_holder_features(holder_pre, signal_date=signal_date))
        row.update(
            _margin_features(
                margin_pre,
                expected_source_date=expected_source_date,
            )
        )
        records.append(row)

    output = pd.DataFrame(records)
    expected = [
        "asof_date",
        "stock_id",
        *PRICE_FEATURES,
        *INSTITUTIONAL_FEATURES,
        *MAIN_FORCE_FEATURES,
        *HOLDER_FEATURES,
        *MARGIN_FEATURES,
    ]
    for column in expected:
        if column not in output:
            output[column] = np.nan
    return output[expected]


def summarize_feature_groups(
    rows: pd.DataFrame,
    *,
    features: Iterable[str] = NUMERIC_PRE_SIGNAL_FEATURES,
    scope: str,
) -> pd.DataFrame:
    """Summarize numeric pre-signal features for each D+5 group."""
    records: list[dict[str, Any]] = []
    for feature in features:
        if feature not in rows:
            continue
        values = pd.to_numeric(rows[feature], errors="coerce")
        for group_key, group in rows.assign(_value=values).groupby("d5_group", sort=False):
            valid = group["_value"].dropna()
            records.append(
                {
                    "scope": scope,
                    "d5_group": group_key,
                    "d5_group_label": group["d5_group_label"].iloc[0],
                    "feature": feature,
                    "group_rows": int(len(group)),
                    "feature_rows": int(len(valid)),
                    "coverage": _safe_divide(len(valid), len(group)),
                    "mean": valid.mean(),
                    "median": valid.median(),
                    "q25": valid.quantile(0.25),
                    "q75": valid.quantile(0.75),
                }
            )
    return pd.DataFrame(records)


def compare_gain_groups_with_loss(
    rows: pd.DataFrame,
    *,
    features: Iterable[str] = NUMERIC_PRE_SIGNAL_FEATURES,
    scope: str,
) -> pd.DataFrame:
    """Compare each gain group with the loss group using robust and standardized gaps."""
    loss = rows[rows["d5_group"].eq("D5_LOSS")]
    records: list[dict[str, Any]] = []
    for target_key in ("D5_GAIN_10_20", "D5_GAIN_GE_20"):
        target = rows[rows["d5_group"].eq(target_key)]
        if target.empty or loss.empty:
            continue
        for feature in features:
            if feature not in rows:
                continue
            target_values = pd.to_numeric(target[feature], errors="coerce").dropna()
            loss_values = pd.to_numeric(loss[feature], errors="coerce").dropna()
            pooled = pd.concat([target_values, loss_values], ignore_index=True)
            pooled_std = float(pooled.std(ddof=0)) if len(pooled) else np.nan
            mean_difference = target_values.mean() - loss_values.mean()
            records.append(
                {
                    "scope": scope,
                    "target_group": target_key,
                    "target_group_label": target["d5_group_label"].iloc[0],
                    "reference_group": "D5_LOSS",
                    "feature": feature,
                    "target_rows": int(len(target_values)),
                    "reference_rows": int(len(loss_values)),
                    "target_coverage": _safe_divide(len(target_values), len(target)),
                    "reference_coverage": _safe_divide(len(loss_values), len(loss)),
                    "target_mean": target_values.mean(),
                    "reference_mean": loss_values.mean(),
                    "target_median": target_values.median(),
                    "reference_median": loss_values.median(),
                    "median_difference": target_values.median() - loss_values.median(),
                    "mean_difference": mean_difference,
                    "standardized_mean_difference": (
                        mean_difference / pooled_std
                        if np.isfinite(pooled_std) and pooled_std > 0
                        else np.nan
                    ),
                }
            )
    return pd.DataFrame(records)


def build_univariate_holdout_reference(
    rows: pd.DataFrame,
    *,
    features: Iterable[str] = NUMERIC_PRE_SIGNAL_FEATURES,
    discovery_end: str = "2026-03-31",
    holdout_start: str = "2026-04-01",
    min_discovery_class_rows: int = 15,
    min_holdout_selected_rows: int = 15,
) -> pd.DataFrame:
    """Screen one-feature thresholds learned before an untouched holdout.

    This is deliberately not a fitted strategy.  A direction and midpoint
    threshold are learned on the discovery period, then frozen and reported on
    the later holdout.  It is useful for feature triage while keeping the output
    shadow-only and multiple-testing aware.
    """
    required = {"asof_date", "d5_close_date", "d5_group"}
    missing = required - set(rows.columns)
    if missing:
        raise ValueError(f"rows missing split columns: {sorted(missing)}")

    frame = rows.copy()
    frame["asof_date"] = pd.to_datetime(frame["asof_date"], errors="coerce")
    frame["d5_close_date"] = pd.to_datetime(
        frame["d5_close_date"], errors="coerce"
    )
    discovery_cutoff = pd.Timestamp(discovery_end)
    discovery_signal_scope = frame["asof_date"].le(discovery_cutoff)
    discovery_mature_scope = frame["d5_close_date"].le(discovery_cutoff)
    discovery = frame[discovery_signal_scope & discovery_mature_scope]
    holdout = frame[frame["asof_date"] >= pd.Timestamp(holdout_start)]
    discovery_purged_rows = int(
        (discovery_signal_scope & ~discovery_mature_scope).sum()
    )
    tasks = {
        "D5_GAIN_GE10_VS_LOSS": {"D5_GAIN_10_20", "D5_GAIN_GE_20"},
        "D5_GAIN_GE20_VS_LOSS": {"D5_GAIN_GE_20"},
    }
    records: list[dict[str, Any]] = []
    for task, positive_groups in tasks.items():
        discovery_task = discovery[
            discovery["d5_group"].isin(positive_groups | {"D5_LOSS"})
        ].copy()
        holdout_task = holdout[
            holdout["d5_group"].isin(positive_groups | {"D5_LOSS"})
        ].copy()
        for feature in features:
            if feature not in frame:
                continue
            train_values = pd.to_numeric(discovery_task[feature], errors="coerce")
            train_target = discovery_task["d5_group"].isin(positive_groups)
            positive_values = train_values[train_target].dropna()
            negative_values = train_values[~train_target].dropna()
            if (
                len(positive_values) < min_discovery_class_rows
                or len(negative_values) < min_discovery_class_rows
            ):
                continue
            positive_median = float(positive_values.median())
            negative_median = float(negative_values.median())
            direction = "HIGHER" if positive_median >= negative_median else "LOWER"
            threshold = (positive_median + negative_median) / 2.0

            test_values = pd.to_numeric(holdout_task[feature], errors="coerce")
            test_target = holdout_task["d5_group"].isin(positive_groups)
            available = test_values.notna()
            selected = available & (
                test_values.ge(threshold) if direction == "HIGHER" else test_values.le(threshold)
            )
            available_rows = int(available.sum())
            selected_rows = int(selected.sum())
            available_positive = int((available & test_target).sum())
            selected_positive = int((selected & test_target).sum())
            base_rate = _safe_divide(available_positive, available_rows)
            precision = _safe_divide(selected_positive, selected_rows)
            records.append(
                {
                    "task": task,
                    "feature": feature,
                    "discovery_end": discovery_end,
                    "holdout_start": holdout_start,
                    "discovery_label_maturity_purged_rows": discovery_purged_rows,
                    "direction": direction,
                    "threshold": threshold,
                    "discovery_positive_rows": int(len(positive_values)),
                    "discovery_loss_rows": int(len(negative_values)),
                    "discovery_positive_median": positive_median,
                    "discovery_loss_median": negative_median,
                    "holdout_available_rows": available_rows,
                    "holdout_selected_rows": selected_rows,
                    "holdout_selected_positive_rows": selected_positive,
                    "holdout_base_rate": base_rate,
                    "holdout_precision": precision,
                    "holdout_lift": (
                        precision / base_rate
                        if np.isfinite(precision) and np.isfinite(base_rate) and base_rate > 0
                        else np.nan
                    ),
                    "holdout_selection_coverage": _safe_divide(
                        selected_rows, available_rows
                    ),
                    "meets_min_holdout_rows": selected_rows >= min_holdout_selected_rows,
                }
            )
    return pd.DataFrame(records)


def _prepare_signals(signals: pd.DataFrame) -> pd.DataFrame:
    required = {"asof_date", "stock_id"}
    missing = required - set(signals.columns)
    if missing:
        raise ValueError(f"signals missing required columns: {sorted(missing)}")
    output = signals[["asof_date", "stock_id"]].copy()
    output["signal_date"] = pd.to_datetime(output["asof_date"], errors="raise")
    output["stock_id"] = output["stock_id"].map(_normalize_stock_id)
    return output[["signal_date", "stock_id"]]


def _prepare_long_history(frame: pd.DataFrame, *, date_column: str) -> pd.DataFrame:
    if frame is None or frame.empty:
        return pd.DataFrame(columns=[date_column, "stock_id"])
    output = frame.copy()
    if date_column not in output or "stock_id" not in output:
        raise ValueError(f"history requires {date_column!r} and 'stock_id'")
    output[date_column] = pd.to_datetime(output[date_column], errors="coerce")
    output["stock_id"] = output["stock_id"].map(_normalize_stock_id)
    return output.dropna(subset=[date_column]).sort_values(["stock_id", date_column])


def _prepare_wide_panel(panel: pd.DataFrame | None) -> pd.DataFrame:
    if panel is None or panel.empty:
        return pd.DataFrame()
    output = panel.copy()
    output.index = pd.to_datetime(output.index, errors="coerce")
    output = output[~output.index.isna()].sort_index()
    output.columns = [_normalize_stock_id(column) for column in output.columns]
    return output.loc[:, ~output.columns.duplicated()]


def _group_by_stock(frame: pd.DataFrame) -> dict[str, pd.DataFrame]:
    if frame.empty:
        return {}
    return {str(stock_id): group for stock_id, group in frame.groupby("stock_id", sort=False)}


def _strictly_before(
    frame: pd.DataFrame | None, signal_date: pd.Timestamp, date_column: str
) -> pd.DataFrame:
    if frame is None or frame.empty:
        return pd.DataFrame()
    return frame[frame[date_column] < signal_date].copy()


def _strict_holder_history(
    frame: pd.DataFrame | None, signal_date: pd.Timestamp
) -> pd.DataFrame:
    if frame is None or frame.empty:
        return pd.DataFrame()
    output = frame[frame["date"] < signal_date].copy()
    if "holder_source_date" not in output:
        return pd.DataFrame()
    output["holder_source_date"] = pd.to_datetime(
        output["holder_source_date"], errors="coerce"
    )
    output = output[output["holder_source_date"] < signal_date]
    if "alignment_status" in output:
        output = output[output["alignment_status"].eq("ok")]
    if "source_kind" in output:
        output = output[output["source_kind"].notna()]
    return output.sort_values(["holder_source_date", "date"])


def _strict_margin_history(
    frame: pd.DataFrame | None, signal_date: pd.Timestamp
) -> pd.DataFrame:
    if frame is None or frame.empty:
        return pd.DataFrame()
    output = frame[frame["trade_date"] < signal_date].copy()
    if "available_date" not in output:
        return pd.DataFrame()
    output["available_date"] = pd.to_datetime(output["available_date"], errors="coerce")
    return output[output["available_date"] < signal_date].sort_values("trade_date")


def _price_features(
    frame: pd.DataFrame,
    *,
    expected_source_date: pd.Timestamp | None,
) -> dict[str, Any]:
    output = {column: np.nan for column in PRICE_FEATURES}
    if frame.empty:
        return output
    values = frame.sort_values("date")
    latest = values.iloc[-1]
    if not _matches_expected_source_date(
        latest.get("date"), expected_source_date
    ):
        return output
    tail5 = values.tail(5)
    close = pd.to_numeric(values.get("close"), errors="coerce")
    open_price = pd.to_numeric(values.get("open"), errors="coerce")
    volume = pd.to_numeric(values.get("volume"), errors="coerce")
    body_pct = ((close / open_price) - 1.0).abs() * 100.0
    tail5_body = body_pct.loc[tail5.index]

    output.update(
        {
            "pre_price_source_date": _date_text(latest.get("date")),
            "pre_return_1d_pct": _period_return_pct(close, 1),
            "pre_return_5d_pct": _period_return_pct(close, 5),
            "pre_return_20d_pct": _period_return_pct(close, 20),
            "pre_close_to_sma20_pct": _fraction_to_pct(latest.get("sma20_gap")),
            "pre_range_pos_20": _number(latest.get("range_pos_20")),
            "pre_day_volume_ratio_20": _number(latest.get("day_volume_ratio_20")),
            "pre5_mean_day_volume_ratio_20": _mean(tail5.get("day_volume_ratio_20")),
            "pre5_max_day_volume_ratio_20": _max(tail5.get("day_volume_ratio_20")),
            "pre5_min_abs_open_close_pct": _min(tail5_body),
            "pre5_tight_body_count_le_1_2pct": int(
                tail5_body.le(1.2 + PERCENT_BOUNDARY_TOLERANCE).sum()
            ),
            "pre5_tight_body_exists_le_1_2pct": bool(
                tail5_body.le(1.2 + PERCENT_BOUNDARY_TOLERANCE).any()
            ),
            "pre5_mean_turnover_million_twd": _mean(
                (close.loc[tail5.index] * volume.loc[tail5.index]) / 1_000_000.0
            ),
            "pre5_upper_tail_count": _flag_sum(tail5.get("upper_tail_flag")),
            "pre5_volume_exhaustion_count": _flag_sum(
                tail5.get("volume_exhaustion_flag")
            ),
            "pre5_late_chase_count": _flag_sum(tail5.get("late_chase_risk_flag")),
        }
    )
    return output


def _institutional_features(
    frame: pd.DataFrame,
    price_pre: pd.DataFrame,
    *,
    expected_source_date: pd.Timestamp | None,
) -> dict[str, Any]:
    output = {column: np.nan for column in INSTITUTIONAL_FEATURES}
    if frame.empty:
        return output
    values = frame.sort_values("date")
    if "flow_available" in values:
        values = values[pd.to_numeric(values["flow_available"], errors="coerce").eq(1)]
    if values.empty:
        return output
    latest = values.iloc[-1]
    if not _matches_expected_source_date(
        latest.get("date"), expected_source_date
    ):
        return output
    tail5 = values.tail(5)
    volume_by_date = _volume_by_date(price_pre)
    five_day_volume = _aligned_volume_sum(tail5["date"], volume_by_date)
    one_day_volume = _aligned_volume_sum(values.tail(1)["date"], volume_by_date)
    foreign = _numeric_series(values.get("foreign_net_buy_shares"))
    institutional = _numeric_series(values.get("institutional_net_buy_shares"))
    output.update(
        {
            "pre_institutional_source_date": _date_text(latest.get("date")),
            "pre_foreign_net_shares_1d": _sum(foreign.tail(1)),
            "pre_foreign_net_shares_5d": _sum(foreign.tail(5)),
            "pre_foreign_net_volume_ratio_1d_pct": _ratio_pct(
                _sum(foreign.tail(1)), one_day_volume
            ),
            "pre_foreign_net_volume_ratio_5d_pct": _ratio_pct(
                _sum(foreign.tail(5)), five_day_volume
            ),
            "pre_trust_net_volume_ratio_5d_pct": _ratio_pct(
                _sum(_numeric_series(tail5.get("trust_net_buy_shares"))), five_day_volume
            ),
            "pre_dealer_net_volume_ratio_5d_pct": _ratio_pct(
                _sum(_numeric_series(tail5.get("dealer_net_buy_shares"))), five_day_volume
            ),
            "pre_institutional_net_volume_ratio_5d_pct": _ratio_pct(
                _sum(institutional.tail(5)), five_day_volume
            ),
            "pre_foreign_positive_day_ratio_5d": _positive_ratio(foreign.tail(5)),
            "pre_institutional_positive_day_ratio_5d": _positive_ratio(
                institutional.tail(5)
            ),
        }
    )
    return output


def _wide_flow_features(
    panel: pd.DataFrame,
    *,
    stock_id: str,
    signal_date: pd.Timestamp,
    price_pre: pd.DataFrame,
    prefix: str,
    expected_source_date: pd.Timestamp | None,
) -> dict[str, Any]:
    if prefix == "main_force":
        output = {column: np.nan for column in MAIN_FORCE_FEATURES[:5]}
    else:
        output = {column: np.nan for column in MAIN_FORCE_FEATURES[5:]}
    if panel.empty or stock_id not in panel:
        return output
    values = pd.to_numeric(panel.loc[panel.index < signal_date, stock_id], errors="coerce")
    values = values.dropna().sort_index()
    if values.empty:
        return output
    if not _matches_expected_source_date(values.index[-1], expected_source_date):
        return output
    if prefix == "main_force":
        tail5 = values.tail(5)
        volume_lots = _aligned_volume_sum(
            pd.Series(tail5.index), _volume_by_date(price_pre)
        ) / 1_000.0
        output.update(
            {
                "pre_main_force_source_date": _date_text(values.index[-1]),
                "pre_main_force_net_lots_1d": _sum(values.tail(1)),
                "pre_main_force_net_lots_5d": _sum(tail5),
                "pre_main_force_net_volume_ratio_5d_pct": _ratio_pct(
                    _sum(tail5), volume_lots
                ),
                "pre_main_force_positive_day_ratio_5d": _positive_ratio(tail5),
            }
        )
    else:
        output.update(
            {
                "pre_broker_count_source_date": _date_text(values.index[-1]),
                "pre_broker_count_diff_1d": _sum(values.tail(1)),
                "pre_broker_count_diff_5d_sum": _sum(values.tail(5)),
            }
        )
    return output


def _holder_features(
    frame: pd.DataFrame, *, signal_date: pd.Timestamp
) -> dict[str, Any]:
    output = {column: np.nan for column in HOLDER_FEATURES}
    if frame.empty:
        return output
    snapshots = frame.drop_duplicates("holder_source_date", keep="last").sort_values(
        "holder_source_date"
    )
    latest = snapshots.iloc[-1]
    ratio = _numeric_series(snapshots.get("big_holder_ratio_1000_lots_pct"))
    count = _numeric_series(snapshots.get("big_holder_count_1000_lots"))
    source_date = pd.Timestamp(latest["holder_source_date"])
    output.update(
        {
            "pre_holder_source_date": _date_text(source_date),
            "pre_holder_lag_days": float((signal_date - source_date).days),
            "pre_big_holder_ratio_1000_lots_pct": _number(
                latest.get("big_holder_ratio_1000_lots_pct")
            ),
            "pre_big_holder_ratio_delta_1w_pctpt": _period_difference(ratio, 1),
            "pre_big_holder_ratio_delta_4w_pctpt": _period_difference(ratio, 4),
            "pre_big_holder_count_delta_1w": _period_difference(count, 1),
            "pre_big_holder_count_delta_4w": _period_difference(count, 4),
        }
    )
    return output


def _margin_features(
    frame: pd.DataFrame,
    *,
    expected_source_date: pd.Timestamp | None,
) -> dict[str, Any]:
    output = {column: np.nan for column in MARGIN_FEATURES}
    if frame.empty:
        return output
    values = frame.sort_values("trade_date")
    latest = values.iloc[-1]
    if not _matches_expected_source_date(
        latest.get("available_date"), expected_source_date
    ):
        return output
    balance = _numeric_series(values.get("margin_balance"))
    output.update(
        {
            "pre_margin_source_date": _date_text(latest.get("trade_date")),
            "pre_margin_available_date": _date_text(latest.get("available_date")),
            "pre_margin_balance": _number(latest.get("margin_balance")),
            "pre_margin_balance_change_5d_pct": _period_return_pct(balance, 5),
            "pre_margin_balance_change_20d_pct": _period_return_pct(balance, 20),
        }
    )
    return output


def _expected_prior_market_date(
    market_dates: pd.DatetimeIndex,
    signal_date: pd.Timestamp,
) -> pd.Timestamp | None:
    if market_dates.empty:
        return None
    position = market_dates.searchsorted(signal_date, side="left") - 1
    if position < 0:
        return None
    return pd.Timestamp(market_dates[position]).normalize()


def _prepare_market_calendar(
    market_calendar: Iterable[Any] | pd.DataFrame,
) -> pd.DatetimeIndex:
    if isinstance(market_calendar, pd.DataFrame):
        if "date" not in market_calendar.columns:
            raise ValueError("market_calendar DataFrame must contain a date column")
        values: Iterable[Any] = market_calendar["date"]
    else:
        values = market_calendar
    parsed = pd.to_datetime(list(values), errors="coerce")
    dates = pd.DatetimeIndex(parsed).dropna().normalize().drop_duplicates().sort_values()
    if dates.empty:
        raise ValueError("market_calendar must contain at least one valid market date")
    return dates


def _matches_expected_source_date(
    value: Any,
    expected_source_date: pd.Timestamp | None,
) -> bool:
    if expected_source_date is None or pd.isna(expected_source_date):
        return False
    source_date = pd.to_datetime(value, errors="coerce")
    if pd.isna(source_date):
        return False
    return pd.Timestamp(source_date).normalize() == pd.Timestamp(
        expected_source_date
    ).normalize()


def _volume_by_date(price_pre: pd.DataFrame) -> pd.Series:
    if price_pre.empty or "volume" not in price_pre:
        return pd.Series(dtype=float)
    output = pd.Series(
        pd.to_numeric(price_pre["volume"], errors="coerce").to_numpy(),
        index=pd.to_datetime(price_pre["date"]),
    )
    return output[~output.index.duplicated(keep="last")]


def _aligned_volume_sum(dates: pd.Series, volume_by_date: pd.Series) -> float:
    if volume_by_date.empty:
        return np.nan
    index = pd.to_datetime(dates, errors="coerce")
    aligned = volume_by_date.reindex(index)
    if aligned.isna().any():
        return np.nan
    return float(aligned.sum())


def _period_return_pct(values: pd.Series, periods: int) -> float:
    numeric = _numeric_series(values).dropna()
    if len(numeric) <= periods:
        return np.nan
    current = float(numeric.iloc[-1])
    previous = float(numeric.iloc[-1 - periods])
    if previous == 0:
        return np.nan
    return (current / previous - 1.0) * 100.0


def _period_difference(values: pd.Series, periods: int) -> float:
    numeric = _numeric_series(values).dropna()
    if len(numeric) <= periods:
        return np.nan
    return float(numeric.iloc[-1] - numeric.iloc[-1 - periods])


def _numeric_series(values: Any) -> pd.Series:
    if values is None:
        return pd.Series(dtype=float)
    return pd.to_numeric(pd.Series(values), errors="coerce")


def _fraction_to_pct(value: Any) -> float:
    number = _number(value)
    return number * 100.0 if np.isfinite(number) else np.nan


def _normalize_stock_id(value: Any) -> str:
    text = str(value).strip()
    if text.endswith(".0") and text[:-2].isdigit():
        text = text[:-2]
    return text.zfill(4)


def _date_text(value: Any) -> str | float:
    parsed = pd.to_datetime(value, errors="coerce")
    return parsed.strftime("%Y-%m-%d") if pd.notna(parsed) else np.nan


def _number(value: Any) -> float:
    number = pd.to_numeric(pd.Series([value]), errors="coerce").iloc[0]
    return float(number) if pd.notna(number) else np.nan


def _sum(values: Any) -> float:
    numeric = _numeric_series(values).dropna()
    return float(numeric.sum()) if len(numeric) else np.nan


def _mean(values: Any) -> float:
    numeric = _numeric_series(values).dropna()
    return float(numeric.mean()) if len(numeric) else np.nan


def _min(values: Any) -> float:
    numeric = _numeric_series(values).dropna()
    return float(numeric.min()) if len(numeric) else np.nan


def _max(values: Any) -> float:
    numeric = _numeric_series(values).dropna()
    return float(numeric.max()) if len(numeric) else np.nan


def _flag_sum(values: Any) -> float:
    numeric = _numeric_series(values).dropna()
    return float(numeric.ne(0).sum()) if len(numeric) else np.nan


def _positive_ratio(values: Any) -> float:
    numeric = _numeric_series(values).dropna()
    return float(numeric.gt(0).mean()) if len(numeric) else np.nan


def _ratio_pct(numerator: float, denominator: float) -> float:
    if not np.isfinite(numerator) or not np.isfinite(denominator) or denominator == 0:
        return np.nan
    return numerator / denominator * 100.0


def _safe_divide(numerator: float, denominator: float) -> float:
    return numerator / denominator if denominator else np.nan
