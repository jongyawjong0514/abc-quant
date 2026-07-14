"""Build the calibrated, grouped Zhu Walkline shadow decision surface.

This historical sidecar fits only on discovery/validation/calibration splits,
evaluates the untouched holdout, and writes prediction-only rows separately
from evaluator rows. It never changes formal strategy state.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sqlite3
import sys
from typing import Any

import numpy as np
import pandas as pd
import yaml


REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
for path in (REPO_ROOT, SRC_ROOT):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from abc_quant.validation.d10_probability_challenger import (  # noqa: E402
    fit_probability_challenger,
    predict_probability_challenger,
)
from abc_quant.validation.expected_return_model import (  # noqa: E402
    evaluate_expected_return,
    fit_expected_return_model,
    predict_expected_return,
)
from abc_quant.validation.forward_outcome_surface import (  # noqa: E402
    build_forward_outcomes,
    build_monotone_probability_surface,
    evaluate_forward_probability_surface,
)
from abc_quant.validation.pit_grouping import (  # noqa: E402
    ALLOWED_MARKET_REGIMES,
    INSUFFICIENT_FEATURES,
    beta_binomial_partial_pool,
    build_pit_groupings,
)


MODE = "shadow_observation_only"
SPLITS = ("DISCOVERY", "VALIDATION", "CALIBRATION", "HOLDOUT")
TARGETS = {
    "raw_p_gt0": lambda value: value >= 0.0,
    "raw_p_ge10": lambda value: value >= 10.0,
    "raw_p_ge20": lambda value: value >= 20.0,
    "raw_p_tail_loss_le_minus3": lambda value: value <= -3.0,
}
PREDICTION_COLUMNS = [
    "asof_date",
    "observation_date",
    "stock_id",
    "split",
    "p_gt0",
    "p_ge10",
    "p_ge20",
    "p_tail_loss_le_minus3",
    "p_loss_lt_0",
    "p_gain_0_10",
    "p_gain_10_20",
    "p_gain_ge_20",
    "probability_edge",
    "probability_edge_status",
    "expected_net_return_pct",
    "expected_return_status",
    "ranking_status",
    "universe_status",
    "sector",
    "sector_source_date",
    "sector_effective_date",
    "sector_available_date",
    "sector_pit_status",
    "market_percentile",
    "sector_within_percentile",
    "size_tier",
    "liquidity_tier",
    "market_regime",
    "market_regime_source",
    "concept_status",
    "grouping_mode",
    "mode",
    "formal_trade_effect",
]


def run_analysis(config: dict[str, Any]) -> dict[str, Any]:
    """Fit the fixed probability surfaces and archive holdout diagnostics."""

    data_config = config["data"]
    analysis = config["analysis"]
    model_config = config["model"]
    grouping_config = config["grouping"]
    output_dir = _repo_path(analysis["output_dir"])
    output_dir.mkdir(parents=True, exist_ok=True)

    rows = pd.read_parquet(_repo_path(data_config["modeling_parquet"]))
    rows = validate_modeling_rows(rows)
    source_summary = json.loads(
        _repo_path(data_config["source_summary_json"]).read_text(encoding="utf-8")
    )
    technical_features = tuple(source_summary["factor_manifest"]["technical_features"])
    missing_features = sorted(set(technical_features).difference(rows.columns))
    if missing_features:
        raise ValueError(f"modeling rows missing technical features: {missing_features}")

    return_values = pd.to_numeric(rows["net_return_pct"], errors="raise")
    outcome_rows = build_forward_outcomes(return_values)
    raw_probabilities, model_audit = fit_probability_targets(
        rows,
        return_values=return_values,
        feature_names=technical_features,
        model_config=model_config,
    )
    probability_surface = build_monotone_probability_surface(
        raw_probabilities,
        raw_p_gt0_column="raw_p_gt0",
        raw_p_ge10_column="raw_p_ge10",
        raw_p_ge20_column="raw_p_ge20",
        raw_tail_loss_column="raw_p_tail_loss_le_minus3",
    )
    expected_return, return_model_audit = fit_expected_returns(
        rows,
        return_values=return_values,
        feature_names=technical_features,
        model_config=model_config,
    )
    return_metrics = build_return_metrics(rows, return_values, expected_return)
    return_status = expected_return_validation_status(return_metrics)

    prediction_base = rows[
        ["asof_date", "observation_date", "stock_id", "split"]
    ].copy()
    prediction_base = pd.concat(
        [prediction_base, probability_surface, expected_return], axis=1
    )
    prediction_base["probability_edge"] = (
        prediction_base["p_ge10"]
        - prediction_base["p_tail_loss_le_minus3"]
    )
    prediction_base["probability_edge_status"] = (
        "UNVALIDATED_POST_HOLDOUT_MUTATION"
    )
    prediction_base["score"] = prediction_base["expected_net_return_pct"]
    prediction_base = attach_point_in_time_groups(
        prediction_base,
        modeling_rows=rows,
        sqlite_path=Path(data_config["sqlite_path"]),
        grouping_config=grouping_config,
    )
    prediction_base["expected_return_status"] = return_status
    prediction_base["universe_status"] = (
        "EVALUATION_ONLY_LABEL_FILTERED_UNIVERSE"
    )
    if return_status == "HOLDOUT_VALIDATED":
        prediction_base["ranking_status"] = "HOLDOUT_VALIDATED"
    else:
        prediction_base["market_percentile"] = np.nan
        prediction_base["sector_within_percentile"] = np.nan
        prediction_base["ranking_status"] = INSUFFICIENT_FEATURES
    prediction_base["mode"] = MODE
    prediction_base["formal_trade_effect"] = False

    probability_metrics = build_probability_metrics(
        rows, probability_surface, return_values
    )
    holdout = rows["split"].eq("HOLDOUT")
    group_metrics = build_group_metrics(
        prediction_base.loc[holdout],
        return_values.loc[holdout],
        minimum_group_rows=int(grouping_config["minimum_group_rows"]),
        prior_alpha=float(grouping_config["beta_prior_alpha"]),
        prior_beta=float(grouping_config["beta_prior_beta"]),
    )
    top_decile = build_top_decile_metrics(
        prediction_base.loc[holdout], return_values.loc[holdout]
    )
    regime_coverage = build_market_regime_coverage(prediction_base.loc[holdout])

    prediction_holdout = prediction_base.loc[holdout, PREDICTION_COLUMNS].copy()
    evaluator_holdout = prediction_holdout.copy()
    evaluator_holdout["d5_net_return_pct"] = return_values.loc[holdout].to_numpy()
    evaluator_holdout["outcome_class"] = outcome_rows.loc[
        holdout, "outcome_class"
    ].to_numpy()
    evaluator_holdout["tail_loss_le_minus3"] = outcome_rows.loc[
        holdout, "tail_loss_le_minus3"
    ].to_numpy()

    paths = write_outputs(
        output_dir=output_dir,
        prediction_holdout=prediction_holdout,
        evaluator_holdout=evaluator_holdout,
        probability_metrics=probability_metrics,
        return_metrics=return_metrics,
        group_metrics=group_metrics,
        top_decile=top_decile,
        regime_coverage=regime_coverage,
        model_audit=model_audit,
        return_model_audit=return_model_audit,
        expected_return_status=return_status,
        config=config,
    )
    return {
        "prediction_rows": prediction_holdout,
        "evaluator_rows": evaluator_holdout,
        "probability_metrics": probability_metrics,
        "return_metrics": return_metrics,
        "group_metrics": group_metrics,
        "top_decile": top_decile,
        "regime_coverage": regime_coverage,
        "paths": paths,
    }


def validate_modeling_rows(rows: pd.DataFrame) -> pd.DataFrame:
    required = {
        "asof_date",
        "observation_date",
        "stock_id",
        "split",
        "technical_source_date",
        "net_return_pct",
        "return_20d",
        "volatility_20d_pct",
    }
    missing = required - set(rows.columns)
    if missing:
        raise ValueError(f"modeling rows missing decision columns: {sorted(missing)}")
    output = rows.copy()
    output["observation_date"] = pd.to_datetime(
        output["observation_date"], errors="raise"
    )
    output["technical_source_date"] = pd.to_datetime(
        output["technical_source_date"], errors="raise"
    )
    if output["technical_source_date"].gt(output["observation_date"]).any():
        raise ValueError("technical source date is after observation date")
    if not output["split"].isin(SPLITS).all():
        raise ValueError("modeling rows contain unknown splits")
    if output.duplicated(["observation_date", "stock_id"]).any():
        raise ValueError("modeling rows contain duplicate stock dates")
    return output


def fit_probability_targets(
    rows: pd.DataFrame,
    *,
    return_values: pd.Series,
    feature_names: tuple[str, ...],
    model_config: dict[str, Any],
) -> tuple[pd.DataFrame, dict[str, Any]]:
    split_rows = {split: rows[rows["split"].eq(split)] for split in SPLITS}
    raw = pd.DataFrame(index=rows.index)
    audit: dict[str, Any] = {}
    for column, target_function in TARGETS.items():
        labels = return_values.map(target_function).astype(int)
        model = fit_probability_challenger(
            split_rows["DISCOVERY"],
            labels.loc[split_rows["DISCOVERY"].index],
            split_rows["VALIDATION"],
            labels.loc[split_rows["VALIDATION"].index],
            split_rows["CALIBRATION"],
            labels.loc[split_rows["CALIBRATION"].index],
            feature_names=feature_names,
            l2_grid=model_config["l2_grid"],
            selection_metric=str(model_config["selection_metric"]),
            max_iterations=int(model_config["maximum_iterations"]),
            tolerance=float(model_config["tolerance"]),
        )
        raw[column] = predict_probability_challenger(model, rows)
        selected = min(
            model.validation_scores,
            key=lambda score: (
                getattr(score, str(model_config["selection_metric"])),
                score.l2_penalty,
            ),
        )
        audit[column] = {
            "selected_l2_penalty": selected.l2_penalty,
            "validation_brier": selected.brier,
            "validation_logloss": selected.logloss,
            "optimizer_converged": model.logistic_model.converged,
            "platt_converged": model.platt_calibrator.converged,
        }
    return raw, audit


def fit_expected_returns(
    rows: pd.DataFrame,
    *,
    return_values: pd.Series,
    feature_names: tuple[str, ...],
    model_config: dict[str, Any],
) -> tuple[pd.DataFrame, dict[str, Any]]:
    split_rows = {split: rows[rows["split"].eq(split)] for split in SPLITS}
    model = fit_expected_return_model(
        split_rows["DISCOVERY"],
        return_values.loc[split_rows["DISCOVERY"].index],
        split_rows["VALIDATION"],
        return_values.loc[split_rows["VALIDATION"].index],
        split_rows["CALIBRATION"],
        return_values.loc[split_rows["CALIBRATION"].index],
        feature_names=feature_names,
        l2_grid=model_config["l2_grid"],
    )
    prediction = predict_expected_return(model, rows)
    return (
        pd.DataFrame({"expected_net_return_pct": prediction}, index=rows.index),
        {
            "selected_l2_penalty": model.l2_penalty,
            "calibration_intercept": model.calibration_intercept,
            "calibration_slope": model.calibration_slope,
            "validation_scores": [score.__dict__ for score in model.validation_scores],
        },
    )


def attach_point_in_time_groups(
    predictions: pd.DataFrame,
    *,
    modeling_rows: pd.DataFrame,
    sqlite_path: Path,
    grouping_config: dict[str, Any],
) -> pd.DataFrame:
    observations = predictions.copy()
    observations = attach_liquidity(observations, sqlite_path=sqlite_path)
    label_free_market = load_label_free_market_features(
        sqlite_path,
        start_date=observations["observation_date"].min().date().isoformat(),
        end_date=observations["observation_date"].max().date().isoformat(),
    )
    date_splits = modeling_rows[["observation_date", "split"]].drop_duplicates()
    if date_splits.duplicated("observation_date").any():
        raise ValueError("one observation date cannot belong to multiple splits")
    label_free_market = label_free_market.merge(
        date_splits,
        on="observation_date",
        how="inner",
        validate="many_to_one",
    )
    observations = attach_market_state(
        observations,
        market_rows=label_free_market,
        trend_threshold_pct=float(
            grouping_config["market_trend_return20_threshold_pct"]
        ),
        reference_split=str(grouping_config["market_volatility_reference_split"]),
    )
    observations["market_regime_source"] = "label_free_full_market_raw_prices"
    sector_history = load_sector_history(
        sqlite_path,
        start_date=observations["observation_date"].min().date().isoformat(),
        end_date=observations["observation_date"].max().date().isoformat(),
        table=str(grouping_config["pit_sector_table"]),
        allowed_modes=set(grouping_config["allowed_membership_modes"]),
    )
    grouped = build_pit_groupings(
        observations,
        sector_history=sector_history,
        concept_history=None,
        score_column="score",
    )
    return grouped


def load_sector_history(
    sqlite_path: Path,
    *,
    start_date: str,
    end_date: str,
    table: str,
    allowed_modes: set[str],
) -> pd.DataFrame:
    if table != "stock_pit_sector_membership_daily":
        raise ValueError("only the audited PIT sector table is allowed")
    query = f"""
        select date, stock_id, collection_name as sector, membership_mode,
               effective_source_date
        from {table}
        where date between ? and ? and collection_layer = 'sector'
    """
    with sqlite3.connect(sqlite_path) as connection:
        frame = pd.read_sql_query(query, connection, params=[start_date, end_date])
    frame = frame[frame["membership_mode"].isin(allowed_modes)].copy()
    frame["stock_id"] = frame["stock_id"].astype(str).str.zfill(4)
    frame["daily_membership_date"] = pd.to_datetime(frame["date"], errors="raise")
    source = pd.to_datetime(frame["effective_source_date"], errors="coerce")
    if source.isna().any():
        raise ValueError("sector effective source date is missing")
    if source.gt(frame["daily_membership_date"]).any():
        raise ValueError("sector effective source date exceeds observation date")
    frame["effective_date"] = source
    frame["available_date"] = source
    conflict = (
        frame.groupby(["stock_id", "effective_date"])["sector"].nunique().gt(1)
    )
    if conflict.any():
        raise ValueError("sector history conflicts at the same effective source date")
    frame = frame.sort_values(
        ["stock_id", "effective_date", "daily_membership_date"]
    ).drop_duplicates(["stock_id", "effective_date"], keep="last")
    return frame[["stock_id", "sector", "effective_date", "available_date"]]


def attach_liquidity(
    observations: pd.DataFrame, *, sqlite_path: Path
) -> pd.DataFrame:
    start = (
        pd.Timestamp(observations["observation_date"].min())
        - pd.Timedelta(days=60)
    ).date().isoformat()
    end = pd.Timestamp(observations["observation_date"].max()).date().isoformat()
    query = """
        select date, stock_id, close, volume
        from daily_ohlcv_features
        where date between ? and ? and length(stock_id) = 4
        order by stock_id, date
    """
    with sqlite3.connect(sqlite_path) as connection:
        prices = pd.read_sql_query(query, connection, params=[start, end])
    prices["observation_date"] = pd.to_datetime(prices["date"], errors="raise")
    prices["stock_id"] = prices["stock_id"].astype(str).str.zfill(4)
    prices["turnover_twd"] = pd.to_numeric(prices["close"], errors="coerce") * pd.to_numeric(
        prices["volume"], errors="coerce"
    )
    prices["avg_turnover_20_twd"] = (
        prices.groupby("stock_id", sort=False)["turnover_twd"]
        .rolling(20, min_periods=20)
        .mean()
        .reset_index(level=0, drop=True)
    )
    liquidity = prices[
        ["observation_date", "stock_id", "avg_turnover_20_twd"]
    ]
    output = observations.merge(
        liquidity,
        on=["observation_date", "stock_id"],
        how="left",
        validate="one_to_one",
    )
    output["free_float_market_cap"] = np.nan
    return output


def load_label_free_market_features(
    sqlite_path: Path, *, start_date: str, end_date: str
) -> pd.DataFrame:
    query_start = (
        pd.Timestamp(start_date) - pd.Timedelta(days=70)
    ).date().isoformat()
    query = """
        select date, stock_id, close
        from daily_ohlcv_features
        where date between ? and ? and length(stock_id) = 4
        order by stock_id, date
    """
    with sqlite3.connect(sqlite_path) as connection:
        prices = pd.read_sql_query(
            query, connection, params=[query_start, end_date]
        )
    prices["observation_date"] = pd.to_datetime(prices["date"], errors="raise")
    prices["stock_id"] = prices["stock_id"].astype(str).str.zfill(4)
    prices["close"] = pd.to_numeric(prices["close"], errors="coerce")
    grouped = prices.groupby("stock_id", sort=False)["close"]
    prices["return_1d"] = grouped.pct_change(fill_method=None)
    prices["return_20d"] = grouped.pct_change(20, fill_method=None) * 100.0
    prices["volatility_20d_pct"] = (
        prices.groupby("stock_id", sort=False)["return_1d"]
        .rolling(20, min_periods=20)
        .std(ddof=0)
        .reset_index(level=0, drop=True)
        * 100.0
    )
    return prices.loc[
        prices["observation_date"].between(
            pd.Timestamp(start_date), pd.Timestamp(end_date)
        ),
        [
            "observation_date",
            "stock_id",
            "return_20d",
            "volatility_20d_pct",
        ],
    ].copy()


def attach_market_state(
    observations: pd.DataFrame,
    *,
    market_rows: pd.DataFrame,
    trend_threshold_pct: float,
    reference_split: str = "DISCOVERY",
) -> pd.DataFrame:
    observations = observations.copy()
    observations["observation_date"] = pd.to_datetime(
        observations["observation_date"], errors="raise"
    )
    daily = (
        market_rows.assign(
            _return20_pct=pd.to_numeric(
                market_rows["return_20d"], errors="coerce"
            ),
            _volatility=pd.to_numeric(
                market_rows["volatility_20d_pct"], errors="coerce"
            ),
        )
        .groupby("observation_date", as_index=False)
        .agg(
            market_return20_median_pct=("_return20_pct", "median"),
            market_volatility_median=("_volatility", "median"),
        )
    )
    discovery_dates = set(
        pd.to_datetime(
            market_rows.loc[
                market_rows["split"].eq(reference_split), "observation_date"
            ]
        )
    )
    reference = daily[
        pd.to_datetime(daily["observation_date"]).isin(discovery_dates)
    ]["market_volatility_median"].median()
    daily["market_trend"] = np.select(
        [
            daily["market_return20_median_pct"].gt(trend_threshold_pct),
            daily["market_return20_median_pct"].lt(-trend_threshold_pct),
        ],
        ["up", "down"],
        default="flat",
    )
    daily["market_volatility"] = np.where(
        daily["market_volatility_median"].ge(reference), "high", "low"
    )
    return observations.merge(
        daily[["observation_date", "market_trend", "market_volatility"]],
        on="observation_date",
        how="left",
        validate="many_to_one",
    )


def build_probability_metrics(
    rows: pd.DataFrame,
    probability_surface: pd.DataFrame,
    return_values: pd.Series,
) -> pd.DataFrame:
    records: list[pd.DataFrame] = []
    for split in SPLITS:
        mask = rows["split"].eq(split)
        metrics = evaluate_forward_probability_surface(
            return_values.loc[mask], probability_surface.loc[mask]
        )
        metrics.insert(0, "split", split)
        records.append(metrics)
    return pd.concat(records, ignore_index=True)


def build_return_metrics(
    rows: pd.DataFrame,
    return_values: pd.Series,
    expected_return: pd.DataFrame,
) -> pd.DataFrame:
    records: list[dict[str, Any]] = []
    for split in SPLITS:
        mask = rows["split"].eq(split)
        metrics = evaluate_expected_return(
            return_values.loc[mask],
            expected_return.loc[mask, "expected_net_return_pct"],
        )
        records.append({"split": split, **metrics})
    return pd.DataFrame(records)


def expected_return_validation_status(return_metrics: pd.DataFrame) -> str:
    """Fail closed when the expected-return sidecar has no usable holdout edge."""

    holdout = return_metrics[return_metrics["split"].eq("HOLDOUT")]
    if len(holdout) != 1:
        return "DIAGNOSTIC_UNTRUSTED"
    correlation = pd.to_numeric(holdout.iloc[0]["correlation"], errors="coerce")
    bias = pd.to_numeric(holdout.iloc[0]["mean_bias"], errors="coerce")
    if (
        not np.isfinite(correlation)
        or not np.isfinite(bias)
        or correlation < 0.05
        or abs(bias) > 1.0
    ):
        return "DIAGNOSTIC_UNTRUSTED"
    return "HOLDOUT_VALIDATED"


def build_group_metrics(
    predictions: pd.DataFrame,
    returns: pd.Series,
    *,
    minimum_group_rows: int,
    prior_alpha: float = 1.0,
    prior_beta: float = 1.0,
) -> pd.DataFrame:
    if prior_alpha <= 0.0 or prior_beta <= 0.0:
        raise ValueError("beta prior alpha and beta must be positive")
    prior_strength = prior_alpha + prior_beta
    prior_mean = prior_alpha / prior_strength
    frame = predictions.copy()
    frame["actual_return"] = returns.to_numpy()
    frame["gain_ge10"] = frame["actual_return"].ge(10.0)
    records: list[pd.DataFrame] = []
    for dimension in ("sector", "liquidity_tier", "market_regime", "size_tier"):
        grouped = (
            frame.groupby(dimension, dropna=False, as_index=False)
            .agg(
                trials=("stock_id", "size"),
                successes=("gain_ge10", "sum"),
                mean_net_return_pct=("actual_return", "mean"),
                median_net_return_pct=("actual_return", "median"),
                mean_p_ge10=("p_ge10", "mean"),
                mean_tail_probability=("p_tail_loss_le_minus3", "mean"),
            )
            .rename(columns={dimension: "group"})
        )
        pooled = beta_binomial_partial_pool(
            grouped,
            prior_strength=prior_strength,
            prior_mean=prior_mean,
        )
        pooled.insert(0, "dimension", dimension)
        pooled["minimum_group_rows_met"] = pooled["trials"].ge(minimum_group_rows)
        records.append(pooled)
    return pd.concat(records, ignore_index=True)


def build_top_decile_metrics(
    predictions: pd.DataFrame, returns: pd.Series
) -> pd.DataFrame:
    frame = predictions.copy()
    frame["actual_return"] = returns.to_numpy()
    threshold = frame["p_ge10"].quantile(0.90)
    selected = frame[frame["p_ge10"].ge(threshold)]
    values = selected["actual_return"]
    return pd.DataFrame(
        [
            {
                "selection": "holdout_top_decile_p_ge10",
                "threshold": threshold,
                "selected_rows": len(selected),
                "coverage": len(selected) / len(frame) if len(frame) else 0.0,
                "precision_gain_ge10": values.ge(10.0).mean(),
                "gain_ge20_rate": values.ge(20.0).mean(),
                "loss_rate": values.lt(0.0).mean(),
                "tail_loss_rate": values.le(-3.0).mean(),
                "mean_net_return_pct": values.mean(),
                "median_net_return_pct": values.median(),
            }
        ]
    )


def build_market_regime_coverage(predictions: pd.DataFrame) -> pd.DataFrame:
    counts = predictions["market_regime"].value_counts(dropna=False)
    total = len(predictions)
    return pd.DataFrame(
        [
            {
                "market_regime": regime,
                "rows": int(counts.get(regime, 0)),
                "coverage": float(counts.get(regime, 0) / total) if total else 0.0,
                "evaluated": bool(counts.get(regime, 0) > 0),
            }
            for regime in sorted(ALLOWED_MARKET_REGIMES)
        ]
    )


def write_outputs(
    *,
    output_dir: Path,
    prediction_holdout: pd.DataFrame,
    evaluator_holdout: pd.DataFrame,
    probability_metrics: pd.DataFrame,
    return_metrics: pd.DataFrame,
    group_metrics: pd.DataFrame,
    top_decile: pd.DataFrame,
    regime_coverage: pd.DataFrame,
    model_audit: dict[str, Any],
    return_model_audit: dict[str, Any],
    expected_return_status: str,
    config: dict[str, Any],
) -> dict[str, Path]:
    paths = {
        "predictions": output_dir
        / "zhu_walkline_shadow_holdout_predictions_for_evaluation.csv",
        "evaluator": output_dir / "zhu_walkline_shadow_decision_evaluator.csv",
        "probability_metrics": output_dir / "zhu_walkline_shadow_probability_metrics.csv",
        "return_metrics": output_dir / "zhu_walkline_shadow_expected_return_metrics.csv",
        "group_metrics": output_dir / "zhu_walkline_shadow_group_metrics.csv",
        "top_decile": output_dir / "zhu_walkline_shadow_top_decile_metrics.csv",
        "regime_coverage": output_dir
        / "zhu_walkline_shadow_market_regime_coverage.csv",
        "summary_json": output_dir / "zhu_walkline_shadow_decision_surface_summary.json",
        "summary_md": output_dir / "zhu_walkline_shadow_decision_surface_report.md",
    }
    for key, frame in (
        ("predictions", prediction_holdout),
        ("evaluator", evaluator_holdout),
        ("probability_metrics", probability_metrics),
        ("return_metrics", return_metrics),
        ("group_metrics", group_metrics),
        ("top_decile", top_decile),
        ("regime_coverage", regime_coverage),
    ):
        frame.to_csv(paths[key], index=False, encoding="utf-8-sig")
    summary = {
        "as_of": config["analysis"]["as_of"],
        "market": config["analysis"]["market"],
        "currency": config["analysis"]["currency"],
        "timezone": config["analysis"]["timezone"],
        "horizon": config["analysis"]["horizon"],
        "mode": MODE,
        "formal_champion_changed": False,
        "formal_trade_effect": False,
        "live_deployable": False,
        "prediction_rows": len(prediction_holdout),
        "probability_models": model_audit,
        "expected_return_model": return_model_audit,
        "expected_return_status": expected_return_status,
        "ranking_status": (
            "HOLDOUT_VALIDATED"
            if expected_return_status == "HOLDOUT_VALIDATED"
            else INSUFFICIENT_FEATURES
        ),
        "probability_edge_status": "UNVALIDATED_POST_HOLDOUT_MUTATION",
        "universe_status": "EVALUATION_ONLY_LABEL_FILTERED_UNIVERSE",
        "beta_prior_alpha": float(config["grouping"]["beta_prior_alpha"]),
        "beta_prior_beta": float(config["grouping"]["beta_prior_beta"]),
        "concept_status": "insufficient_data",
        "size_status": INSUFFICIENT_FEATURES,
        "paid_in_capital_fallback_used": False,
        "promotion_decision": "blocked_before_promotion_review",
        "artifacts": {key: str(path) for key, path in paths.items()},
    }
    paths["summary_json"].write_text(
        json.dumps(_json_safe(summary), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    paths["summary_md"].write_text(
        render_report(
            summary,
            probability_metrics,
            return_metrics,
            group_metrics,
            top_decile,
            regime_coverage,
        ),
        encoding="utf-8",
    )
    return paths


def render_report(
    summary: dict[str, Any],
    probability_metrics: pd.DataFrame,
    return_metrics: pd.DataFrame,
    group_metrics: pd.DataFrame,
    top_decile: pd.DataFrame,
    regime_coverage: pd.DataFrame,
) -> str:
    holdout_probability = probability_metrics[
        probability_metrics["split"].eq("HOLDOUT")
    ][
        [
            "target",
            "evaluation_rows",
            "brier",
            "logloss",
            "calibration_gap",
            "coverage",
        ]
    ]
    holdout_return = return_metrics[return_metrics["split"].eq("HOLDOUT")]
    comparable_groups = group_metrics[
        group_metrics["minimum_group_rows_met"]
        & ~group_metrics["group"].astype(str).eq(INSUFFICIENT_FEATURES)
    ]
    lines = [
        "# Zhu Walkline 影子決策面",
        "",
        "## 研究邊界",
        "",
        f"- as_of：`{summary['as_of']}`",
        f"- horizon：`{summary['horizon']}`",
        "- 訓練／選模／校準／holdout 完全依時間分開。",
        "- `holdout_predictions_for_evaluation` 不含 D+5 結果欄，但列集合經標籤成熟度／公司行動篩選，只能作歷史評估，不是 live 候選池。",
        "- 規模分層因缺 point-in-time 自由流通市值而標記 `INSUFFICIENT_FEATURES`。",
        "- 概念股歷史不足，標記 `insufficient_data`，禁止目前名單回填。",
        "- 預期報酬模型未通過 holdout 時，市場／產業 percentile 一律留空；不得改用看過 holdout 才提出的機率差排序。",
        "",
        "## Holdout 機率品質",
        "",
        _markdown_table(holdout_probability),
        "",
        f"## Holdout 預期報酬（{summary['expected_return_status']}）",
        "",
        _markdown_table(holdout_return),
        "",
        "## P(>=10%) 前 10%",
        "",
        _markdown_table(top_decile),
        "",
        "## 市場狀態覆蓋",
        "",
        _markdown_table(regime_coverage),
        "",
        "## 可比較分組（至少 20 筆）",
        "",
        _markdown_table(
            comparable_groups[
                [
                    "dimension",
                    "group",
                    "trials",
                    "raw_rate",
                    "pooled_rate",
                    "mean_net_return_pct",
                ]
            ].head(40)
        ),
        "",
        "```text",
        "mode=shadow_observation_only",
        "formal_champion_changed=False",
        "formal_trade_effect=False",
        "promotion_decision=blocked_before_promotion_review",
        "```",
    ]
    return "\n".join(lines) + "\n"


def _markdown_table(frame: pd.DataFrame) -> str:
    if frame.empty:
        return "_No rows._"
    columns = list(frame.columns)
    header = "| " + " | ".join(columns) + " |"
    separator = "|" + "|".join(["---"] * len(columns)) + "|"
    body = []
    for row in frame.itertuples(index=False, name=None):
        values = []
        for value in row:
            if isinstance(value, float):
                values.append("" if not np.isfinite(value) else f"{value:.6f}")
            else:
                values.append(str(value))
        body.append("| " + " | ".join(values) + " |")
    return "\n".join([header, separator, *body])


def _json_safe(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(item) for item in value]
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating, float)):
        return float(value) if np.isfinite(value) else None
    if isinstance(value, Path):
        return str(value)
    return value


def _repo_path(value: str | Path) -> Path:
    path = Path(value)
    return path if path.is_absolute() else REPO_ROOT / path


def _load_config(path: Path) -> dict[str, Any]:
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("decision surface config must be a mapping")
    return payload


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--config",
        default="config/zhu_walkline_shadow_decision_surface.yaml",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    result = run_analysis(_load_config(_repo_path(args.config)))
    print(f"holdout_prediction_rows={len(result['prediction_rows'])}")
    print("mode=shadow_observation_only")
    print("formal_champion_changed=False")
    print("formal_trade_effect=False")
    print("promotion_decision=blocked_before_promotion_review")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
