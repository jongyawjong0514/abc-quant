"""Web/news event scoring with strict no-lookahead filters."""

from __future__ import annotations

from typing import Any

import pandas as pd


SOURCE_SCORE_CAP = {
    "official": 5.0,
    "reliable_media": 3.0,
    "community": 0.0,
}


def compute_news_event_features(
    web_records: list[dict[str, Any]],
    *,
    asof_date: str,
    web_score_cap: float = 5.0,
) -> pd.DataFrame:
    """Score web event records without using post-asof or unknown-date records."""
    if not web_records:
        return pd.DataFrame(
            columns=[
                "stock_id",
                "event_score_for_rise",
                "event_score_for_fall",
                "event_source_quality_score",
            ]
        )
    cutoff = pd.to_datetime(asof_date)
    rows: list[dict[str, Any]] = []
    for record in web_records:
        stock_id = str(record.get("stock_id", "")).strip()
        if not stock_id:
            continue
        priority = str(record.get("source_priority", "community"))
        published_unknown = bool(record.get("published_at_unknown", False))
        published_at = pd.to_datetime(record.get("published_at"), errors="coerce")
        if published_unknown or pd.isna(published_at) or published_at > cutoff:
            score_cap = 0.0
        else:
            score_cap = min(SOURCE_SCORE_CAP.get(priority, 0.0), web_score_cap)
        sentiment = float(record.get("event_sentiment_score", 0.0) or 0.0)
        rise = max(0.0, sentiment) * score_cap
        fall = max(0.0, -sentiment) * score_cap
        rows.append(
            {
                "stock_id": stock_id,
                "has_recent_mops_event": priority == "official",
                "has_recent_revenue_news": bool(record.get("has_recent_revenue_news", False)),
                "has_recent_earnings_news": bool(record.get("has_recent_earnings_news", False)),
                "has_recent_law_conference": bool(record.get("has_recent_law_conference", False)),
                "has_recent_product_news": bool(record.get("has_recent_product_news", False)),
                "has_recent_customer_news": bool(record.get("has_recent_customer_news", False)),
                "has_recent_warning_news": bool(record.get("has_recent_warning_news", False)),
                "event_sentiment_score": sentiment,
                "event_confidence_score": _confidence_score(record.get("confidence")),
                "event_source_quality_score": score_cap,
                "event_score_for_rise": rise,
                "event_score_for_fall": fall,
            }
        )
    if not rows:
        return pd.DataFrame()
    frame = pd.DataFrame(rows)
    aggregations = {
        "has_recent_mops_event": "max",
        "has_recent_revenue_news": "max",
        "has_recent_earnings_news": "max",
        "has_recent_law_conference": "max",
        "has_recent_product_news": "max",
        "has_recent_customer_news": "max",
        "has_recent_warning_news": "max",
        "event_sentiment_score": "mean",
        "event_confidence_score": "max",
        "event_source_quality_score": "max",
        "event_score_for_rise": "sum",
        "event_score_for_fall": "sum",
    }
    result = frame.groupby("stock_id", as_index=False).agg(aggregations)
    result["event_score_for_rise"] = result["event_score_for_rise"].clip(0, web_score_cap)
    result["event_score_for_fall"] = result["event_score_for_fall"].clip(0, web_score_cap)
    return result


def _confidence_score(value: object) -> float:
    return {"high": 1.0, "medium": 0.6, "low": 0.3}.get(str(value), 0.0)
