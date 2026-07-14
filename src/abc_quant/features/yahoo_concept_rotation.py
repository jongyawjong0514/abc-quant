"""As-of Yahoo concept breadth and hierarchical shadow context gates."""

from __future__ import annotations

from pathlib import Path
import sqlite3
from typing import Any

import numpy as np
import pandas as pd

from abc_quant.data.yahoo_concepts import membership_mode_for_date


ALLOWED_MARKET_STATES = {
    "MARKET_STRONG_UPTREND",
    "MARKET_PULLBACK_IN_UPTREND",
    "MARKET_RANGE_BOUND",
}
ALLOWED_SECTOR_STATES = {"SECTOR_LEADING", "SECTOR_ROTATING_IN"}
ALLOWED_CONCEPT_STATES = {"CONCEPT_LEADING", "CONCEPT_ROTATING_IN"}

CONCEPT_ROTATION_COLUMNS = [
    "snapshot_id",
    "snapshot_date",
    "asof_date",
    "concept_name",
    "member_count",
    "price_available_count",
    "coverage_ratio",
    "above_sma20_ratio",
    "sma20_slope_positive_ratio",
    "positive_return_5d_ratio",
    "median_return_5d_pct",
    "concept_strength_score",
    "concept_state",
    "membership_mode",
]

CONCEPT_CONTEXT_COLUMNS = [
    "concept_memberships",
    "best_concept_name",
    "concept_state",
    "concept_strength_score",
    "concept_member_count",
    "concept_price_available_count",
    "concept_coverage_ratio",
    "concept_above_sma20_ratio",
    "concept_sma20_slope_positive_ratio",
    "concept_positive_return_5d_ratio",
    "concept_median_return_5d_pct",
    "concept_snapshot_id",
    "concept_snapshot_date",
    "concept_membership_mode",
]


def compute_yahoo_concept_rotation(
    price_features: pd.DataFrame,
    membership: pd.DataFrame,
    *,
    snapshot_date: str,
    allow_static_current_backfill: bool,
    min_available_members: int = 3,
    date_from: str | None = None,
    date_to: str | None = None,
) -> pd.DataFrame:
    """Compute concept breadth from current-or-prior rows only.

    Static membership may be projected backward only when explicitly enabled.
    Price features remain as-of: SMA slope uses t versus t-1 and the five-day
    return uses t versus t-5.
    """

    if price_features.empty or membership.empty:
        return pd.DataFrame(columns=CONCEPT_ROTATION_COLUMNS)
    _require_columns(price_features, {"date", "stock_id", "close", "sma20"})
    _require_columns(membership, {"snapshot_id", "concept_name", "stock_id"})

    members = membership[["snapshot_id", "concept_name", "stock_id"]].copy()
    members["stock_id"] = members["stock_id"].astype(str).str.zfill(4)
    members = members.drop_duplicates(["snapshot_id", "concept_name", "stock_id"])
    prices = price_features[["date", "stock_id", "close", "sma20"]].copy()
    prices["stock_id"] = prices["stock_id"].astype(str).str.zfill(4)
    prices["date"] = pd.to_datetime(prices["date"], errors="coerce")
    prices["close"] = pd.to_numeric(prices["close"], errors="coerce")
    prices["sma20"] = pd.to_numeric(prices["sma20"], errors="coerce")
    prices = (
        prices.dropna(subset=["date"])
        .sort_values(["stock_id", "date"])
        .drop_duplicates(["stock_id", "date"], keep="last")
    )
    stock_groups = prices.groupby("stock_id", sort=False)
    prices["_sma20_prev"] = stock_groups["sma20"].shift(1)
    prices["_close_5d"] = stock_groups["close"].shift(5)
    prices["_return_5d_pct"] = (prices["close"] / prices["_close_5d"] - 1.0) * 100.0

    expanded = members.merge(prices, on="stock_id", how="inner")
    valid_above = expanded[["close", "sma20"]].notna().all(axis=1)
    valid_slope = expanded[["sma20", "_sma20_prev"]].notna().all(axis=1)
    valid_return = expanded[["close", "_close_5d"]].notna().all(axis=1)
    expanded["_metric_available"] = valid_above & valid_slope & valid_return
    expanded["_above_sma20"] = np.where(
        valid_above, (expanded["close"] > expanded["sma20"]).astype(float), np.nan
    )
    expanded["_sma20_slope_positive"] = np.where(
        valid_slope,
        (expanded["sma20"] > expanded["_sma20_prev"]).astype(float),
        np.nan,
    )
    expanded["_positive_return_5d"] = np.where(
        valid_return,
        (expanded["_return_5d_pct"] > 0.0).astype(float),
        np.nan,
    )

    grouped = (
        expanded.groupby(["snapshot_id", "concept_name", "date"], as_index=False)
        .agg(
            price_available_count=("_metric_available", "sum"),
            above_sma20_ratio=("_above_sma20", "mean"),
            sma20_slope_positive_ratio=("_sma20_slope_positive", "mean"),
            positive_return_5d_ratio=("_positive_return_5d", "mean"),
            median_return_5d_pct=("_return_5d_pct", "median"),
        )
        .rename(columns={"date": "asof_date"})
    )
    member_counts = (
        members.groupby(["snapshot_id", "concept_name"])["stock_id"]
        .nunique()
        .rename("member_count")
        .reset_index()
    )
    grouped = grouped.merge(member_counts, on=["snapshot_id", "concept_name"], how="left")
    grouped["price_available_count"] = grouped["price_available_count"].astype(int)
    grouped["coverage_ratio"] = grouped["price_available_count"] / grouped["member_count"]
    grouped["concept_strength_score"] = 100.0 * (
        0.40 * grouped["above_sma20_ratio"].fillna(0.0)
        + 0.35 * grouped["sma20_slope_positive_ratio"].fillna(0.0)
        + 0.25 * grouped["positive_return_5d_ratio"].fillna(0.0)
    )
    grouped["asof_date"] = pd.to_datetime(grouped["asof_date"]).dt.strftime("%Y-%m-%d")
    grouped["snapshot_date"] = str(snapshot_date)
    grouped["membership_mode"] = grouped["asof_date"].map(
        lambda value: membership_mode_for_date(
            value,
            snapshot_date=str(snapshot_date),
            allow_static_current_backfill=allow_static_current_backfill,
        )
    )
    grouped["concept_state"] = grouped.apply(
        lambda row: _concept_state(row, min_available_members=min_available_members), axis=1
    )
    if date_from is not None:
        grouped = grouped[grouped["asof_date"] >= str(date_from)]
    if date_to is not None:
        grouped = grouped[grouped["asof_date"] <= str(date_to)]
    return _clean_rotation(grouped[CONCEPT_ROTATION_COLUMNS])


def attach_best_yahoo_concept_context(
    candidates: pd.DataFrame,
    *,
    membership: pd.DataFrame,
    rotation: pd.DataFrame,
    snapshot_date: str,
) -> pd.DataFrame:
    """Attach each stock's strongest same-day Yahoo concept state."""

    output = candidates.copy().reset_index(drop=True)
    output["_context_row_id"] = range(len(output))
    output["stock_id"] = output["stock_id"].astype(str).str.zfill(4)
    output["asof_date"] = pd.to_datetime(output["asof_date"]).dt.strftime("%Y-%m-%d")
    for column in CONCEPT_CONTEXT_COLUMNS:
        if column not in output.columns:
            output[column] = ""
    if membership.empty:
        output["concept_state"] = "CONCEPT_UNMAPPED"
        return output.drop(columns=["_context_row_id"])

    members = membership[["snapshot_id", "concept_name", "stock_id"]].copy()
    members["stock_id"] = members["stock_id"].astype(str).str.zfill(4)
    members = members.drop_duplicates(["snapshot_id", "concept_name", "stock_id"])
    candidate_concepts = output[["_context_row_id", "asof_date", "stock_id"]].merge(
        members, on="stock_id", how="left"
    )
    concept_lists = (
        candidate_concepts.dropna(subset=["concept_name"])
        .groupby("_context_row_id")["concept_name"]
        .agg(lambda values: "|".join(sorted(set(str(value) for value in values))))
        .rename("_concept_memberships")
    )
    output = output.merge(concept_lists, on="_context_row_id", how="left")
    output["concept_memberships"] = output["_concept_memberships"].fillna("")
    output = output.drop(columns=["_concept_memberships"])

    if rotation.empty:
        output["concept_state"] = np.where(
            output["concept_memberships"].eq(""), "CONCEPT_UNMAPPED", "CONCEPT_DATA_UNAVAILABLE"
        )
        output["concept_snapshot_id"] = str(members["snapshot_id"].iloc[0])
        output["concept_snapshot_date"] = str(snapshot_date)
        return output.drop(columns=["_context_row_id"])

    context = candidate_concepts.dropna(subset=["concept_name"]).merge(
        rotation,
        on=["snapshot_id", "concept_name", "asof_date"],
        how="left",
    )
    state_priority = {
        "CONCEPT_LEADING": 5,
        "CONCEPT_ROTATING_IN": 4,
        "CONCEPT_NEUTRAL": 3,
        "CONCEPT_WEAK": 2,
        "CONCEPT_INSUFFICIENT": 1,
        "CONCEPT_POINT_IN_TIME_UNAVAILABLE": 0,
    }
    context["_state_priority"] = context["concept_state"].map(state_priority).fillna(-1)
    context["concept_strength_score"] = pd.to_numeric(
        context["concept_strength_score"], errors="coerce"
    )
    best = (
        context.sort_values(
            ["_context_row_id", "_state_priority", "concept_strength_score", "concept_name"],
            ascending=[True, False, False, True],
        )
        .drop_duplicates("_context_row_id")
        .rename(
            columns={
                "concept_name": "_best_concept_name",
                "concept_state": "_concept_state",
                "concept_strength_score": "_concept_strength_score",
                "member_count": "_concept_member_count",
                "price_available_count": "_concept_price_available_count",
                "coverage_ratio": "_concept_coverage_ratio",
                "above_sma20_ratio": "_concept_above_sma20_ratio",
                "sma20_slope_positive_ratio": "_concept_sma20_slope_positive_ratio",
                "positive_return_5d_ratio": "_concept_positive_return_5d_ratio",
                "median_return_5d_pct": "_concept_median_return_5d_pct",
                "snapshot_id": "_concept_snapshot_id",
                "snapshot_date": "_concept_snapshot_date",
                "membership_mode": "_concept_membership_mode",
            }
        )
    )
    mapped_columns = {
        "best_concept_name": "_best_concept_name",
        "concept_state": "_concept_state",
        "concept_strength_score": "_concept_strength_score",
        "concept_member_count": "_concept_member_count",
        "concept_price_available_count": "_concept_price_available_count",
        "concept_coverage_ratio": "_concept_coverage_ratio",
        "concept_above_sma20_ratio": "_concept_above_sma20_ratio",
        "concept_sma20_slope_positive_ratio": "_concept_sma20_slope_positive_ratio",
        "concept_positive_return_5d_ratio": "_concept_positive_return_5d_ratio",
        "concept_median_return_5d_pct": "_concept_median_return_5d_pct",
        "concept_snapshot_id": "_concept_snapshot_id",
        "concept_snapshot_date": "_concept_snapshot_date",
        "concept_membership_mode": "_concept_membership_mode",
    }
    best_columns = ["_context_row_id", *mapped_columns.values()]
    output = output.merge(best[best_columns], on="_context_row_id", how="left")
    for target, source in mapped_columns.items():
        output[target] = output[source].combine_first(output[target].replace("", pd.NA))
        output = output.drop(columns=[source])
    output["concept_state"] = np.where(
        output["concept_memberships"].eq(""),
        "CONCEPT_UNMAPPED",
        output["concept_state"].fillna("CONCEPT_DATA_UNAVAILABLE"),
    )
    output["concept_snapshot_id"] = output["concept_snapshot_id"].fillna(
        str(members["snapshot_id"].iloc[0])
    )
    output["concept_snapshot_date"] = output["concept_snapshot_date"].fillna(
        str(snapshot_date)
    )
    return output.drop(columns=["_context_row_id"])


def apply_hierarchical_context_gate(
    frame: pd.DataFrame,
    *,
    min_driver_score: int,
) -> pd.DataFrame:
    """Apply market, sector, concept, then individual score in that order."""

    output = frame.copy()
    output["market_gate_pass"] = output["market_state"].isin(ALLOWED_MARKET_STATES)
    output["sector_gate_pass"] = output["sector_state"].isin(ALLOWED_SECTOR_STATES)
    output["concept_gate_pass"] = output["concept_state"].isin(ALLOWED_CONCEPT_STATES)
    output["context_alignment_pass"] = (
        output["market_gate_pass"] & output["sector_gate_pass"] & output["concept_gate_pass"]
    )
    output["hierarchy_gate_order"] = "MARKET>SECTOR>CONCEPT>INDIVIDUAL"
    output["hierarchy_gate_stage"] = "MARKET_BLOCKED"
    market_pass = output["market_gate_pass"]
    sector_pass = output["sector_gate_pass"]
    concept_state = output["concept_state"].fillna("").astype(str)
    output.loc[market_pass, "hierarchy_gate_stage"] = "SECTOR_BLOCKED"
    output.loc[market_pass & sector_pass, "hierarchy_gate_stage"] = "CONCEPT_NOT_LEADING"
    output.loc[
        market_pass & sector_pass & concept_state.eq("CONCEPT_UNMAPPED"),
        "hierarchy_gate_stage",
    ] = "CONCEPT_UNMAPPED"
    output.loc[
        market_pass
        & sector_pass
        & concept_state.isin(
            ["CONCEPT_DATA_UNAVAILABLE", "CONCEPT_POINT_IN_TIME_UNAVAILABLE"]
        ),
        "hierarchy_gate_stage",
    ] = "CONCEPT_DATA_UNAVAILABLE"
    output.loc[
        market_pass & sector_pass & concept_state.eq("CONCEPT_INSUFFICIENT"),
        "hierarchy_gate_stage",
    ] = "CONCEPT_INSUFFICIENT"
    output.loc[output["context_alignment_pass"], "hierarchy_gate_stage"] = (
        "INDIVIDUAL_SCORE_BELOW_THRESHOLD"
    )
    driver_pass = pd.to_numeric(output["driver_score"], errors="coerce") >= float(
        min_driver_score
    )
    output["individual_score_gate_pass"] = driver_pass
    output["hierarchy_observation_pass"] = output["context_alignment_pass"] & driver_pass
    output.loc[output["hierarchy_observation_pass"], "hierarchy_gate_stage"] = (
        "HIERARCHY_CONFIRMED"
    )
    output["context_failure_reason"] = np.where(
        output["hierarchy_observation_pass"], "", output["hierarchy_gate_stage"]
    )
    return output


def write_yahoo_concept_rotation(rotation: pd.DataFrame, *, sqlite_path: Path) -> None:
    """Persist derived shadow rotation rows keyed by snapshot and as-of date."""

    if rotation.empty:
        return
    sqlite_path.parent.mkdir(parents=True, exist_ok=True)
    cleaned = rotation[CONCEPT_ROTATION_COLUMNS].copy().where(pd.notna(rotation), None)
    with sqlite3.connect(sqlite_path) as connection:
        connection.executescript(
            """
            create table if not exists yahoo_concept_rotation_daily (
                snapshot_id text not null,
                snapshot_date text not null,
                asof_date text not null,
                concept_name text not null,
                member_count integer,
                price_available_count integer,
                coverage_ratio real,
                above_sma20_ratio real,
                sma20_slope_positive_ratio real,
                positive_return_5d_ratio real,
                median_return_5d_pct real,
                concept_strength_score real,
                concept_state text not null,
                membership_mode text not null,
                primary key (snapshot_id, asof_date, concept_name)
            );
            """
        )
        with connection:
            cleaned.to_sql(
                "yahoo_concept_rotation_stage", connection, if_exists="replace", index=False
            )
            connection.execute(
                """
                insert or replace into yahoo_concept_rotation_daily
                select snapshot_id, snapshot_date, asof_date, concept_name,
                       member_count, price_available_count, coverage_ratio,
                       above_sma20_ratio, sma20_slope_positive_ratio,
                       positive_return_5d_ratio, median_return_5d_pct,
                       concept_strength_score, concept_state, membership_mode
                from yahoo_concept_rotation_stage
                """
            )
            connection.execute("drop table yahoo_concept_rotation_stage")


def _concept_state(row: pd.Series, *, min_available_members: int) -> str:
    if row["membership_mode"] == "point_in_time_unavailable":
        return "CONCEPT_POINT_IN_TIME_UNAVAILABLE"
    if int(row["price_available_count"]) < int(min_available_members):
        return "CONCEPT_INSUFFICIENT"
    score = float(row["concept_strength_score"])
    median_return = _float_or_zero(row["median_return_5d_pct"])
    above_ratio = _float_or_zero(row["above_sma20_ratio"])
    slope_ratio = _float_or_zero(row["sma20_slope_positive_ratio"])
    if score >= 70.0 and median_return > 0.0 and above_ratio >= 0.60:
        return "CONCEPT_LEADING"
    if score >= 60.0 and median_return > 0.0 and slope_ratio >= 0.55:
        return "CONCEPT_ROTATING_IN"
    if score >= 45.0:
        return "CONCEPT_NEUTRAL"
    return "CONCEPT_WEAK"


def _clean_rotation(frame: pd.DataFrame) -> pd.DataFrame:
    output = frame.copy()
    numeric_columns = [
        "coverage_ratio",
        "above_sma20_ratio",
        "sma20_slope_positive_ratio",
        "positive_return_5d_ratio",
        "median_return_5d_pct",
        "concept_strength_score",
    ]
    output[numeric_columns] = output[numeric_columns].round(6)
    return output.sort_values(["asof_date", "concept_name"]).reset_index(drop=True)


def _require_columns(frame: pd.DataFrame, required: set[str]) -> None:
    missing = sorted(required.difference(frame.columns))
    if missing:
        raise ValueError(f"missing required columns: {missing}")


def _float_or_zero(value: Any) -> float:
    if value is None or pd.isna(value):
        return 0.0
    return float(value)
