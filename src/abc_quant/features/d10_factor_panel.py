"""Causal D-10 through D factor panels for Zhu Walkline research.

The builders in this module are deliberately label-free.  Technical factors
may use the observation day's completed OHLCV bar, while institutional factors
are joined with ``allow_exact_matches=False`` so their source date is always
strictly earlier than the observation date.
"""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any

import numpy as np
import pandas as pd

from abc_quant.features.walkline_features import compute_walkline_feature_history


KEY_COLUMNS = ("observation_date", "stock_id")
SOURCE_DATE_COLUMNS = ("technical_source_date", "institutional_source_date")
RETURN_WINDOWS = (1, 3, 5, 10, 20)
MA_WINDOWS = (5, 10, 20, 60)
VOLUME_WINDOWS = (3, 5, 10, 20)
INSTITUTIONAL_WINDOWS = (1, 3, 5, 10)
INSTITUTIONAL_SLOPE_WINDOWS = (3, 5)

_INSTITUTIONAL_INPUT_COLUMNS = {
    "foreign": "foreign_net_buy_shares",
    "trust": "trust_net_buy_shares",
    "dealer": "dealer_net_buy_shares",
    "institutional_total": "institutional_net_buy_shares",
}

_RETURN_FACTOR_COLUMNS = tuple(f"return_{window}d" for window in RETURN_WINDOWS)
_MA_FACTOR_COLUMNS = tuple(
    column
    for window in MA_WINDOWS
    for column in (
        f"close_to_ma{window}_pct",
        f"ma{window}_slope_3d_pct_per_day",
        f"ma{window}_slope_delta_1d_pctpt",
    )
)
_KD_FACTOR_COLUMNS = (
    "kd_k9",
    "kd_d9",
    "kd_spread",
    "kd_k_change_1d",
    "kd_d_change_1d",
    "kd_spread_change_1d",
)
_OSCILLATOR_FACTOR_COLUMNS = (
    "rsi14",
    "atr14_pct",
    "bollinger_pct_b",
    "bollinger_width_pct",
    "volatility_5d_pct",
    "volatility_20d_pct",
)
_MOMENTUM_FACTOR_COLUMNS = (
    "macd_dif_pct",
    "macd_signal_pct",
    "macd_hist_pct",
    "macd_hist_slope_3d_pctpt_per_day",
    "macd_hist_slope_delta_1d_pctpt",
    "mtm10_pct",
    "mtm10_ma10_pct",
    "mtm10_ma_diff_pct",
    "mtm10_slope_5d_pctpt_per_day",
    "mtm10_slope_delta_1d_pctpt",
)
_BAR_FACTOR_COLUMNS = (
    "bar_body_pct",
    "upper_shadow_pct",
    "lower_shadow_pct",
    "range_position",
)
_VOLUME_FACTOR_COLUMNS = (
    "volume_ma3",
    "volume_ma5",
    "volume_ma10",
    "volume_ma20",
    "volume_ratio_3",
    "volume_ratio_5",
    "volume_ratio_10",
    "volume_ratio_20",
    "volume_ma5_to_ma20_ratio",
    "volume_zscore_20",
    "volume_cv_5",
    "volume_cv_20",
    "turnover_ma5_million_twd",
    "turnover_ma20_million_twd",
    "turnover_ratio_20",
    *tuple(
        column
        for window in (3, 5, 10)
        for column in (
            f"volume_slope_{window}",
            f"volume_slope_{window}_pct_of_mean",
            f"volume_slope_accel_{window}",
            f"volume_slope_accel_{window}_pctpt",
        )
    ),
)
_PRICE_VOLUME_FACTOR_COLUMNS = (
    "obv",
    "obv_slope_5",
    "obv_slope_5_to_volume_ma20",
    "return_volume_corr_5",
    "return_volume_corr_20",
)

TECHNICAL_FACTOR_COLUMNS = (
    *_RETURN_FACTOR_COLUMNS,
    *_MA_FACTOR_COLUMNS,
    *_KD_FACTOR_COLUMNS,
    *_OSCILLATOR_FACTOR_COLUMNS,
    *_MOMENTUM_FACTOR_COLUMNS,
    *_BAR_FACTOR_COLUMNS,
    *_VOLUME_FACTOR_COLUMNS,
    *_PRICE_VOLUME_FACTOR_COLUMNS,
)

INSTITUTIONAL_FACTOR_COLUMNS = tuple(
    column
    for actor in _INSTITUTIONAL_INPUT_COLUMNS
    for column in (
        *(
            factor
            for window in INSTITUTIONAL_WINDOWS
            for factor in (
                f"{actor}_net_volume_ratio_{window}d_pct",
                f"{actor}_buy_day_ratio_{window}d",
            )
        ),
        *(
            factor
            for window in INSTITUTIONAL_SLOPE_WINDOWS
            for factor in (
                f"{actor}_net_volume_ratio_slope_{window}d_pctpt",
                f"{actor}_net_volume_ratio_slope_delta_1d_{window}d_pctpt",
            )
        ),
    )
)

FACTOR_COLUMNS = (*TECHNICAL_FACTOR_COLUMNS, *INSTITUTIONAL_FACTOR_COLUMNS)
ALL_FACTOR_COLUMNS = FACTOR_COLUMNS
D10_FACTOR_COLUMNS = FACTOR_COLUMNS


def build_technical_factor_panel(
    price_history: pd.DataFrame,
    *,
    asof_date: str | pd.Timestamp,
    walkline_history: pd.DataFrame | None = None,
) -> pd.DataFrame:
    """Build causal technical factors for every stock/date through ``asof_date``.

    ``walkline_history`` may be supplied when the caller has already run
    :func:`compute_walkline_feature_history`.  Rows after ``asof_date`` are
    discarded even for a supplied frame.
    """
    cutoff = _as_timestamp(asof_date, name="asof_date")
    if walkline_history is None:
        history = compute_walkline_feature_history(
            price_history,
            asof_date=cutoff.date().isoformat(),
        )
    else:
        history = _prepare_walkline_history(walkline_history, cutoff=cutoff)

    data = history.copy().sort_values(["stock_id", "date"]).reset_index(drop=True)
    data["stock_id"] = data["stock_id"].map(_normalize_stock_id)
    data["date"] = pd.to_datetime(data["date"], errors="raise")
    numeric_inputs = {
        "open",
        "high",
        "low",
        "close",
        "volume",
        *(f"return_{window}d" for window in RETURN_WINDOWS),
        *(f"ma{window}" for window in MA_WINDOWS),
        "kd_k9",
        "kd_d9",
    }
    missing = sorted(numeric_inputs.difference(data.columns))
    if missing:
        raise ValueError("walkline history missing required columns: " + ", ".join(missing))
    for column in numeric_inputs:
        data[column] = pd.to_numeric(data[column], errors="coerce")

    groups = data["stock_id"]
    grouped = data.groupby("stock_id", group_keys=False, sort=False)
    positions = grouped.cumcount().astype(float)
    factors = pd.DataFrame(index=data.index)
    factors["observation_date"] = data["date"]
    factors["stock_id"] = data["stock_id"]
    factors["technical_source_date"] = data["date"]

    for window in RETURN_WINDOWS:
        factors[f"return_{window}d"] = data[f"return_{window}d"]

    for window in MA_WINDOWS:
        ma = data[f"ma{window}"]
        factors[f"close_to_ma{window}_pct"] = _safe_ratio(data["close"], ma).sub(1.0) * 100.0
        prior_ma = grouped[f"ma{window}"].shift(3)
        slope = _safe_ratio(ma, prior_ma).sub(1.0) * (100.0 / 3.0)
        factors[f"ma{window}_slope_3d_pct_per_day"] = slope
        factors[f"ma{window}_slope_delta_1d_pctpt"] = slope.groupby(
            groups, sort=False
        ).diff()

    kd_spread = data["kd_k9"] - data["kd_d9"]
    factors["kd_k9"] = data["kd_k9"]
    factors["kd_d9"] = data["kd_d9"]
    factors["kd_spread"] = kd_spread
    factors["kd_k_change_1d"] = grouped["kd_k9"].diff()
    factors["kd_d_change_1d"] = grouped["kd_d9"].diff()
    factors["kd_spread_change_1d"] = kd_spread.groupby(groups, sort=False).diff()

    close_change = grouped["close"].diff()
    gain = close_change.clip(lower=0.0)
    loss = -close_change.clip(upper=0.0)
    avg_gain = _group_ewm_mean(gain, groups, alpha=1.0 / 14.0, min_periods=14)
    avg_loss = _group_ewm_mean(loss, groups, alpha=1.0 / 14.0, min_periods=14)
    relative_strength = _safe_ratio(avg_gain, avg_loss)
    rsi = 100.0 - 100.0 / (1.0 + relative_strength)
    rsi = rsi.where(~(avg_loss.eq(0.0) & avg_gain.gt(0.0)), 100.0)
    rsi = rsi.where(~(avg_loss.eq(0.0) & avg_gain.eq(0.0)), 50.0)
    factors["rsi14"] = rsi

    previous_close = grouped["close"].shift(1)
    true_range = pd.concat(
        [
            data["high"] - data["low"],
            (data["high"] - previous_close).abs(),
            (data["low"] - previous_close).abs(),
        ],
        axis=1,
    ).max(axis=1)
    atr14 = _group_rolling_mean(true_range, groups, 14)
    factors["atr14_pct"] = _safe_ratio(atr14, data["close"]) * 100.0

    bollinger_mid = _group_rolling_mean(data["close"], groups, 20)
    bollinger_std = _group_rolling_std(data["close"], groups, 20)
    bollinger_upper = bollinger_mid + 2.0 * bollinger_std
    bollinger_lower = bollinger_mid - 2.0 * bollinger_std
    factors["bollinger_pct_b"] = _safe_ratio(
        data["close"] - bollinger_lower,
        bollinger_upper - bollinger_lower,
    )
    factors["bollinger_width_pct"] = _safe_ratio(
        bollinger_upper - bollinger_lower,
        bollinger_mid,
    ) * 100.0
    factors["volatility_5d_pct"] = (
        _group_rolling_std(data["return_1d"], groups, 5) * 100.0
    )
    factors["volatility_20d_pct"] = (
        _group_rolling_std(data["return_1d"], groups, 20) * 100.0
    )

    ema_fast = _group_ewm_mean(
        data["close"], groups, alpha=2.0 / 13.0, min_periods=26
    )
    ema_slow = _group_ewm_mean(
        data["close"], groups, alpha=2.0 / 27.0, min_periods=26
    )
    macd_dif = ema_fast - ema_slow
    macd_signal = _group_ewm_mean(
        macd_dif, groups, alpha=2.0 / 10.0, min_periods=9
    )
    macd_hist_pct = _safe_ratio(macd_dif - macd_signal, data["close"]) * 100.0
    macd_hist_slope = (
        macd_hist_pct - macd_hist_pct.groupby(groups, sort=False).shift(3)
    ) / 3.0
    factors["macd_dif_pct"] = _safe_ratio(macd_dif, data["close"]) * 100.0
    factors["macd_signal_pct"] = _safe_ratio(macd_signal, data["close"]) * 100.0
    factors["macd_hist_pct"] = macd_hist_pct
    factors["macd_hist_slope_3d_pctpt_per_day"] = macd_hist_slope
    factors["macd_hist_slope_delta_1d_pctpt"] = macd_hist_slope.groupby(
        groups, sort=False
    ).diff()

    mtm10_pct = data["return_10d"] * 100.0
    mtm10_ma10_pct = _group_rolling_mean(mtm10_pct, groups, 10)
    mtm10_slope = (
        mtm10_pct - mtm10_pct.groupby(groups, sort=False).shift(5)
    ) / 5.0
    factors["mtm10_pct"] = mtm10_pct
    factors["mtm10_ma10_pct"] = mtm10_ma10_pct
    factors["mtm10_ma_diff_pct"] = mtm10_pct - mtm10_ma10_pct
    factors["mtm10_slope_5d_pctpt_per_day"] = mtm10_slope
    factors["mtm10_slope_delta_1d_pctpt"] = mtm10_slope.groupby(
        groups, sort=False
    ).diff()

    factors["bar_body_pct"] = _safe_ratio(
        data["close"] - data["open"], data["open"]
    ) * 100.0
    factors["upper_shadow_pct"] = _safe_ratio(
        data["high"] - data[["open", "close"]].max(axis=1),
        data["close"],
    ) * 100.0
    factors["lower_shadow_pct"] = _safe_ratio(
        data[["open", "close"]].min(axis=1) - data["low"],
        data["close"],
    ) * 100.0
    factors["range_position"] = _safe_ratio(
        data["close"] - data["low"], data["high"] - data["low"]
    ).fillna(0.5)

    volume_means: dict[int, pd.Series] = {}
    for window in VOLUME_WINDOWS:
        volume_mean = _group_rolling_mean(data["volume"], groups, window)
        volume_means[window] = volume_mean
        factors[f"volume_ma{window}"] = volume_mean
        factors[f"volume_ratio_{window}"] = _safe_ratio(data["volume"], volume_mean)
    factors["volume_ma5_to_ma20_ratio"] = _safe_ratio(
        volume_means[5], volume_means[20]
    )
    volume_std20 = _group_rolling_std(data["volume"], groups, 20)
    factors["volume_zscore_20"] = _safe_ratio(
        data["volume"] - volume_means[20], volume_std20
    )
    factors["volume_cv_5"] = _safe_ratio(
        _group_rolling_std(data["volume"], groups, 5), volume_means[5]
    )
    factors["volume_cv_20"] = _safe_ratio(volume_std20, volume_means[20])

    turnover = data["close"] * data["volume"]
    turnover_ma5 = _group_rolling_mean(turnover, groups, 5)
    turnover_ma20 = _group_rolling_mean(turnover, groups, 20)
    factors["turnover_ma5_million_twd"] = turnover_ma5 / 1_000_000.0
    factors["turnover_ma20_million_twd"] = turnover_ma20 / 1_000_000.0
    factors["turnover_ratio_20"] = _safe_ratio(turnover, turnover_ma20)

    for window in (3, 5, 10):
        slope = _rolling_ols_slope(data["volume"], groups, positions, window)
        normalized_slope = _safe_ratio(slope, volume_means[window]) * 100.0
        factors[f"volume_slope_{window}"] = slope
        factors[f"volume_slope_{window}_pct_of_mean"] = normalized_slope
        factors[f"volume_slope_accel_{window}"] = slope.groupby(groups, sort=False).diff()
        factors[f"volume_slope_accel_{window}_pctpt"] = normalized_slope.groupby(
            groups, sort=False
        ).diff()

    close_direction = np.sign(close_change).fillna(0.0)
    signed_volume = close_direction * data["volume"]
    obv = signed_volume.groupby(groups, sort=False).cumsum()
    obv_slope5 = _rolling_ols_slope(obv, groups, positions, 5)
    factors["obv"] = obv
    factors["obv_slope_5"] = obv_slope5
    factors["obv_slope_5_to_volume_ma20"] = _safe_ratio(obv_slope5, volume_means[20])
    volume_change = grouped["volume"].pct_change(fill_method=None).replace(
        [np.inf, -np.inf], np.nan
    )
    factors["return_volume_corr_5"] = _rolling_corr(
        data["return_1d"], volume_change, groups, 5
    )
    factors["return_volume_corr_20"] = _rolling_corr(
        data["return_1d"], volume_change, groups, 20
    )

    output = factors[[*KEY_COLUMNS, "technical_source_date", *TECHNICAL_FACTOR_COLUMNS]].copy()
    output = output.sort_values(["stock_id", "observation_date"]).reset_index(drop=True)
    assert_factor_panel_point_in_time(output)
    return output


def build_institutional_factor_panel(
    institutional_history: pd.DataFrame | None,
    price_history: pd.DataFrame,
    *,
    asof_date: str | pd.Timestamp,
    date_column: str | None = None,
) -> pd.DataFrame:
    """Build lagged institutional-flow factors for every price observation.

    Net-share inputs are used only as intermediate numerators.  The returned
    panel exposes volume-normalized ratios and direction statistics, never raw
    foreign, trust, dealer, or total share counts.
    """
    cutoff = _as_timestamp(asof_date, name="asof_date")
    observations = _prepare_price_observations(price_history, cutoff=cutoff)
    output_columns = [
        *KEY_COLUMNS,
        "institutional_source_date",
        "institutional_source_lag_calendar_days",
        *INSTITUTIONAL_FACTOR_COLUMNS,
    ]
    if institutional_history is None or institutional_history.empty:
        output = observations[[*KEY_COLUMNS]].copy()
        output["institutional_source_date"] = pd.NaT
        output["institutional_source_lag_calendar_days"] = np.nan
        for column in INSTITUTIONAL_FACTOR_COLUMNS:
            output[column] = np.nan
        return output[output_columns]

    institutional = _prepare_institutional_history(
        institutional_history,
        cutoff=cutoff,
        date_column=date_column,
    )
    if institutional.empty:
        return build_institutional_factor_panel(None, price_history, asof_date=cutoff)

    volumes = observations.rename(columns={"observation_date": "institutional_source_date"})[
        ["institutional_source_date", "stock_id", "volume"]
    ]
    institutional = institutional.merge(
        volumes,
        on=["institutional_source_date", "stock_id"],
        how="left",
        validate="one_to_one",
    )
    institutional = institutional.sort_values(
        ["stock_id", "institutional_source_date"]
    ).reset_index(drop=True)
    groups = institutional["stock_id"]
    positions = institutional.groupby("stock_id", sort=False).cumcount().astype(float)
    features = institutional[["institutional_source_date", "stock_id"]].copy()

    for actor, raw_column in _INSTITUTIONAL_INPUT_COLUMNS.items():
        flow = institutional[raw_column]
        daily_ratio = _safe_ratio(flow, institutional["volume"]) * 100.0
        for window in INSTITUTIONAL_WINDOWS:
            rolling_flow = _group_rolling_sum(flow, groups, window)
            rolling_volume = _group_rolling_sum(institutional["volume"], groups, window)
            features[f"{actor}_net_volume_ratio_{window}d_pct"] = (
                _safe_ratio(rolling_flow, rolling_volume) * 100.0
            )
            buy_indicator = flow.gt(0.0).astype(float).where(flow.notna())
            features[f"{actor}_buy_day_ratio_{window}d"] = _group_rolling_mean(
                buy_indicator, groups, window
            )
        for window in INSTITUTIONAL_SLOPE_WINDOWS:
            slope = _rolling_ols_slope(daily_ratio, groups, positions, window)
            features[f"{actor}_net_volume_ratio_slope_{window}d_pctpt"] = slope
            features[
                f"{actor}_net_volume_ratio_slope_delta_1d_{window}d_pctpt"
            ] = slope.groupby(groups, sort=False).diff()

    left = observations[[*KEY_COLUMNS]].sort_values(
        ["observation_date", "stock_id"]
    )
    right = features.sort_values(["institutional_source_date", "stock_id"])
    output = pd.merge_asof(
        left,
        right,
        left_on="observation_date",
        right_on="institutional_source_date",
        by="stock_id",
        direction="backward",
        allow_exact_matches=False,
    )
    output["institutional_source_lag_calendar_days"] = (
        output["observation_date"] - output["institutional_source_date"]
    ).dt.days.astype(float)
    output = output[output_columns].sort_values(
        ["stock_id", "observation_date"]
    ).reset_index(drop=True)
    assert_factor_panel_point_in_time(output)
    return output


def build_d10_factor_panel(
    price_history: pd.DataFrame,
    *,
    asof_date: str | pd.Timestamp,
    institutional_history: pd.DataFrame | None = None,
    walkline_history: pd.DataFrame | None = None,
) -> pd.DataFrame:
    """Build the combined label-free technical and lagged institutional panel."""
    technical = build_technical_factor_panel(
        price_history,
        asof_date=asof_date,
        walkline_history=walkline_history,
    )
    institutional = build_institutional_factor_panel(
        institutional_history,
        price_history,
        asof_date=asof_date,
    )
    output = technical.merge(
        institutional,
        on=[*KEY_COLUMNS],
        how="left",
        validate="one_to_one",
    )
    assert_factor_panel_point_in_time(output)
    return output


def assert_factor_panel_point_in_time(panel: pd.DataFrame) -> None:
    """Raise ``AssertionError`` when a factor panel violates PIT boundaries."""
    missing = sorted(set(KEY_COLUMNS).difference(panel.columns))
    if missing:
        raise AssertionError("factor panel missing keys: " + ", ".join(missing))
    if panel.duplicated(list(KEY_COLUMNS)).any():
        raise AssertionError("factor panel contains duplicate stock/date keys")

    observation_date = pd.to_datetime(panel["observation_date"], errors="coerce")
    if observation_date.isna().any():
        raise AssertionError("factor panel contains invalid observation dates")
    if "technical_source_date" in panel:
        technical_date = pd.to_datetime(panel["technical_source_date"], errors="coerce")
        invalid = technical_date.notna() & technical_date.gt(observation_date)
        if invalid.any():
            raise AssertionError("technical source date is after observation date")
    if "institutional_source_date" in panel:
        institutional_date = pd.to_datetime(
            panel["institutional_source_date"], errors="coerce"
        )
        invalid = institutional_date.notna() & institutional_date.ge(observation_date)
        if invalid.any():
            raise AssertionError(
                "institutional source date must be strictly before observation date"
            )

    lowered = {str(column).lower(): str(column) for column in panel.columns}
    forbidden_labels = [
        original
        for lowered_column, original in lowered.items()
        if lowered_column.startswith(("future_", "forward_", "label_"))
    ]
    if forbidden_labels:
        raise AssertionError(
            "factor panel contains evaluator-only columns: " + ", ".join(forbidden_labels)
        )
    institution_tokens = ("foreign", "trust", "dealer", "institutional")
    raw_share_columns = [
        original
        for lowered_column, original in lowered.items()
        if "share" in lowered_column
        and any(token in lowered_column for token in institution_tokens)
    ]
    if raw_share_columns:
        raise AssertionError(
            "factor panel exposes raw institutional shares: " + ", ".join(raw_share_columns)
        )


def _prepare_walkline_history(
    walkline_history: pd.DataFrame,
    *,
    cutoff: pd.Timestamp,
) -> pd.DataFrame:
    required = {"date", "stock_id", "open", "high", "low", "close", "volume"}
    missing = sorted(required.difference(walkline_history.columns))
    if missing:
        raise ValueError("walkline history missing required columns: " + ", ".join(missing))
    output = walkline_history.copy()
    output["date"] = pd.to_datetime(output["date"], errors="raise")
    output = output[output["date"].le(cutoff)].copy()
    if output.empty:
        raise ValueError(f"walkline history has no rows at or before {cutoff.date()}")
    return output


def _prepare_price_observations(
    price_history: pd.DataFrame,
    *,
    cutoff: pd.Timestamp,
) -> pd.DataFrame:
    required = {"date", "stock_id", "volume"}
    missing = sorted(required.difference(price_history.columns))
    if missing:
        raise ValueError("price history missing required columns: " + ", ".join(missing))
    output = price_history[["date", "stock_id", "volume"]].copy()
    output["observation_date"] = pd.to_datetime(output.pop("date"), errors="raise")
    output = output[output["observation_date"].le(cutoff)].copy()
    if output.empty:
        raise ValueError(f"price history has no rows at or before {cutoff.date()}")
    output["stock_id"] = output["stock_id"].map(_normalize_stock_id)
    output["volume"] = pd.to_numeric(output["volume"], errors="coerce")
    return (
        output.sort_values(["stock_id", "observation_date"])
        .drop_duplicates(["stock_id", "observation_date"], keep="last")
        .reset_index(drop=True)
    )


def _prepare_institutional_history(
    institutional_history: pd.DataFrame,
    *,
    cutoff: pd.Timestamp,
    date_column: str | None,
) -> pd.DataFrame:
    selected_date_column = date_column
    if selected_date_column is None:
        selected_date_column = "date" if "date" in institutional_history else "trade_date"
    required = {selected_date_column, "stock_id"}
    missing = sorted(required.difference(institutional_history.columns))
    if missing:
        raise ValueError("institutional history missing required columns: " + ", ".join(missing))
    output = institutional_history.copy()
    output["institutional_source_date"] = pd.to_datetime(
        output.pop(selected_date_column), errors="raise"
    )
    output = output[output["institutional_source_date"].le(cutoff)].copy()
    output["stock_id"] = output["stock_id"].map(_normalize_stock_id)
    if "flow_available" in output:
        output = output[pd.to_numeric(output["flow_available"], errors="coerce").eq(1)]
    component_columns = [
        _INSTITUTIONAL_INPUT_COLUMNS[actor]
        for actor in ("foreign", "trust", "dealer")
    ]
    for column in component_columns:
        if column not in output:
            output[column] = np.nan
        output[column] = pd.to_numeric(output[column], errors="coerce")
    total_column = _INSTITUTIONAL_INPUT_COLUMNS["institutional_total"]
    # A partial actor set is not a valid three-institution total.  Keep it
    # missing unless all three components are available or the source provides
    # an explicit total.
    derived_total = output[component_columns].sum(
        axis=1,
        min_count=len(component_columns),
    )
    if total_column not in output:
        output[total_column] = derived_total
    else:
        output[total_column] = pd.to_numeric(output[total_column], errors="coerce").fillna(
            derived_total
        )
    selected = [
        "institutional_source_date",
        "stock_id",
        *_INSTITUTIONAL_INPUT_COLUMNS.values(),
    ]
    return (
        output[selected]
        .sort_values(["stock_id", "institutional_source_date"])
        .drop_duplicates(["stock_id", "institutional_source_date"], keep="last")
        .reset_index(drop=True)
    )


def _group_rolling_sum(
    values: pd.Series,
    groups: pd.Series,
    window: int,
) -> pd.Series:
    numeric = pd.to_numeric(values, errors="coerce")
    return numeric.groupby(groups, sort=False).transform(
        lambda series: series.rolling(window, min_periods=window).sum()
    )


def _group_rolling_mean(
    values: pd.Series,
    groups: pd.Series,
    window: int,
) -> pd.Series:
    numeric = pd.to_numeric(values, errors="coerce")
    return numeric.groupby(groups, sort=False).transform(
        lambda series: series.rolling(window, min_periods=window).mean()
    )


def _group_rolling_std(
    values: pd.Series,
    groups: pd.Series,
    window: int,
) -> pd.Series:
    numeric = pd.to_numeric(values, errors="coerce")
    return numeric.groupby(groups, sort=False).transform(
        lambda series: series.rolling(window, min_periods=window).std(ddof=0)
    )


def _group_ewm_mean(
    values: pd.Series,
    groups: pd.Series,
    *,
    alpha: float,
    min_periods: int,
) -> pd.Series:
    numeric = pd.to_numeric(values, errors="coerce")
    return numeric.groupby(groups, sort=False).transform(
        lambda series: series.ewm(
            alpha=alpha,
            adjust=False,
            min_periods=min_periods,
        ).mean()
    )


def _rolling_ols_slope(
    values: pd.Series,
    groups: pd.Series,
    positions: pd.Series,
    window: int,
) -> pd.Series:
    """Return an equal-spacing rolling OLS slope without per-window Python calls."""
    y = pd.to_numeric(values, errors="coerce")
    x = pd.to_numeric(positions, errors="coerce")
    valid = y.notna() & x.notna()
    valid_count = _group_rolling_sum(valid.astype(float), groups, window)
    sum_y = _group_rolling_sum(y.where(valid), groups, window)
    sum_x = _group_rolling_sum(x.where(valid), groups, window)
    sum_xy = _group_rolling_sum((x * y).where(valid), groups, window)
    sum_x2 = _group_rolling_sum((x * x).where(valid), groups, window)
    numerator = valid_count * sum_xy - sum_x * sum_y
    denominator = valid_count * sum_x2 - sum_x.pow(2)
    slope = _safe_ratio(numerator, denominator)
    return slope.where(valid_count.eq(float(window)))


def _rolling_corr(
    left: pd.Series,
    right: pd.Series,
    groups: pd.Series,
    window: int,
) -> pd.Series:
    x = pd.to_numeric(left, errors="coerce")
    y = pd.to_numeric(right, errors="coerce")
    valid = x.notna() & y.notna()
    count = _group_rolling_sum(valid.astype(float), groups, window)
    sum_x = _group_rolling_sum(x.where(valid), groups, window)
    sum_y = _group_rolling_sum(y.where(valid), groups, window)
    sum_x2 = _group_rolling_sum((x * x).where(valid), groups, window)
    sum_y2 = _group_rolling_sum((y * y).where(valid), groups, window)
    sum_xy = _group_rolling_sum((x * y).where(valid), groups, window)
    numerator = count * sum_xy - sum_x * sum_y
    denominator = np.sqrt(
        (count * sum_x2 - sum_x.pow(2)) * (count * sum_y2 - sum_y.pow(2))
    )
    correlation = _safe_ratio(numerator, denominator)
    return correlation.where(count.eq(float(window))).clip(-1.0, 1.0)


def _safe_ratio(numerator: Any, denominator: Any) -> pd.Series:
    numerator_series = pd.to_numeric(pd.Series(numerator), errors="coerce")
    denominator_series = pd.to_numeric(pd.Series(denominator), errors="coerce")
    result = numerator_series.div(denominator_series.where(denominator_series.ne(0.0)))
    return result.replace([np.inf, -np.inf], np.nan)


def _normalize_stock_id(value: Any) -> str:
    text = str(value).strip()
    if text.endswith(".0") and text[:-2].isdigit():
        text = text[:-2]
    return text.zfill(4)


def _as_timestamp(value: str | pd.Timestamp, *, name: str) -> pd.Timestamp:
    parsed = pd.to_datetime(value, errors="coerce")
    if pd.isna(parsed):
        raise ValueError(f"invalid {name}: {value!r}")
    return pd.Timestamp(parsed)


def forbidden_factor_columns(columns: Iterable[str]) -> list[str]:
    """Return evaluator-only or raw institutional-share columns."""
    output: list[str] = []
    for column in columns:
        lowered = str(column).lower()
        if lowered.startswith(("future_", "forward_", "label_")):
            output.append(str(column))
            continue
        if "share" in lowered and any(
            token in lowered for token in ("foreign", "trust", "dealer", "institutional")
        ):
            output.append(str(column))
    return output
