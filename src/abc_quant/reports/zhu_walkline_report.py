"""Report writers for the Zhu walkline shadow scanner."""

from __future__ import annotations

from pathlib import Path
import json
from typing import Any

import numpy as np
import pandas as pd

from abc_quant.data.local_tw_loader import DataQualityReport
from abc_quant.data.web_cache import write_web_sources_jsonl
from abc_quant.signals.zhu_walkline_shadow import ZhuWalklineResult


RISE_CSV_COLUMNS = [
    "asof_date",
    "stock_id",
    "stock_name",
    "close",
    "rise_score",
    "grade",
    "signal_stage",
    "trigger_type",
    "buy_observation_type",
    "buy_observation_detail_types",
    "buy_trigger_price",
    "buy_trigger_price_role",
    "target_resistance_1",
    "target_resistance_2",
    "sell_warning_type",
    "sell_warning_detail_types",
    "invalidation_price",
    "confirm_price",
    "invalid_price",
    "failure_type",
    "reversal_state",
    "sector",
    "concepts",
    "market_state",
    "sector_rotation_rank",
    "concept_rotation_rank",
    "trend_state",
    "ma_state",
    "kline_state",
    "volume_state",
    "foreign_5d",
    "investment_trust_5d",
    "dealer_5d",
    "institutional_score",
    "big_holder_score",
    "margin_score",
    "web_event_score",
    "support_1",
    "support_2",
    "resistance_1",
    "resistance_2",
    "support_zone_1_low",
    "support_zone_1_high",
    "support_zone_1_label",
    "support_zone_2_low",
    "support_zone_2_high",
    "resistance_zone_1_low",
    "resistance_zone_1_high",
    "resistance_zone_1_label",
    "resistance_zone_2_low",
    "resistance_zone_2_high",
    "support_zone_holding_today",
    "support_zone_failed_today",
    "resistance_zone_breakout_today",
    "resistance_zone_breakout_failed_today",
    "entry_observation",
    "stop_reference",
    "reason_summary",
]

FALL_CSV_COLUMNS = [
    "asof_date",
    "stock_id",
    "stock_name",
    "close",
    "fall_risk_score",
    "risk_grade",
    "signal_stage",
    "failure_type",
    "sell_warning_type",
    "sell_warning_detail_types",
    "invalidation_price",
    "invalid_price",
    "stop_reference",
    "sector",
    "concepts",
    "market_state",
    "trend_state",
    "ma_state",
    "kline_state",
    "volume_state",
    "foreign_5d",
    "investment_trust_5d",
    "dealer_5d",
    "institutional_selling_score",
    "margin_risk_score",
    "web_event_risk_score",
    "support_broken",
    "next_support",
    "support_zone_1_low",
    "support_zone_1_high",
    "support_zone_1_label",
    "broken_support_zone_low",
    "broken_support_zone_high",
    "support_zone_failed_today",
    "risk_reason_summary",
]

SHADOW_LOG_COLUMNS = [
    "asof_date",
    "stock_id",
    "stock_name",
    "close",
    "rise_score",
    "grade",
    "fall_risk_score",
    "risk_grade",
    "signal_stage",
    "trigger_type",
    "buy_observation_type",
    "buy_observation_detail_types",
    "buy_trigger_price",
    "buy_trigger_price_role",
    "target_resistance_1",
    "target_resistance_2",
    "sell_warning_type",
    "sell_warning_detail_types",
    "invalidation_price",
    "confirm_price",
    "invalid_price",
    "failure_type",
    "reversal_state",
    "support_zone_1_low",
    "support_zone_1_high",
    "support_zone_1_label",
    "resistance_zone_1_low",
    "resistance_zone_1_high",
    "resistance_zone_1_label",
    "support_zone_holding_today",
    "support_zone_failed_today",
    "resistance_zone_breakout_today",
    "resistance_zone_breakout_failed_today",
    "institutional_divergence",
    "margin_crowding_risk",
    "high_level_supply_pressure",
    "market_state",
    "sector",
    "trend_state",
    "ma_state",
    "kline_state",
    "volume_state",
    "reason_summary",
    "risk_reason_summary",
    "stop_reference",
]


def write_zhu_walkline_outputs(
    result: ZhuWalklineResult,
    quality: DataQualityReport,
    *,
    output_dir: str | Path,
    evaluation_frame: pd.DataFrame | None = None,
    evaluation_summary: dict[str, Any] | None = None,
) -> dict[str, Path]:
    """Write JSON, CSV, parquet, JSONL, and Markdown outputs."""
    root = Path(output_dir)
    root.mkdir(parents=True, exist_ok=True)
    outputs: dict[str, Path] = {}
    prefixes = ["latest", result.asof_date]
    for prefix in prefixes:
        outputs[f"{prefix}_summary"] = _write_json(
            root / f"{prefix}_zhu_walkline_summary.json",
            _summary_payload(result, quality),
        )
        outputs[f"{prefix}_rise"] = _write_csv(
            root / f"{prefix}_zhu_walkline_top_rise_candidates.csv",
            result.top_rise_candidates,
            RISE_CSV_COLUMNS,
        )
        outputs[f"{prefix}_bullish_watchlist"] = _write_csv(
            root / f"{prefix}_zhu_walkline_top_bullish_watchlist.csv",
            result.top_bullish_watchlist,
            RISE_CSV_COLUMNS,
        )
        outputs[f"{prefix}_fall"] = _write_csv(
            root / f"{prefix}_zhu_walkline_top_fall_risks.csv",
            result.top_fall_risks,
            FALL_CSV_COLUMNS,
        )
        outputs[f"{prefix}_market_report"] = _write_text(
            root / f"{prefix}_zhu_walkline_market_report.md",
            _market_report(result, quality),
        )
        outputs[f"{prefix}_stock_report"] = _write_text(
            root / f"{prefix}_zhu_walkline_stock_report.md",
            _stock_report(result),
        )
        outputs[f"{prefix}_data_quality"] = _write_text(
            root / f"{prefix}_zhu_walkline_data_quality.md",
            _data_quality_report(quality, result),
        )
        parquet_path = root / f"{prefix}_zhu_walkline_feature_matrix.parquet"
        result.feature_matrix.to_parquet(parquet_path, index=False)
        outputs[f"{prefix}_features"] = parquet_path
        web_path = root / f"{prefix}_zhu_walkline_web_sources.jsonl"
        write_web_sources_jsonl(web_path, result.web_records, append=False)
        outputs[f"{prefix}_web_sources"] = web_path
        outputs[f"{prefix}_shadow_log"] = _write_csv(
            root / f"{prefix}_zhu_walkline_shadow_log.csv",
            _shadow_log_frame(result.feature_matrix),
            SHADOW_LOG_COLUMNS,
        )

        if evaluation_frame is not None and evaluation_summary is not None:
            outputs[f"{prefix}_evaluation"] = _write_csv(
                root / f"{prefix}_zhu_walkline_evaluation.csv",
                evaluation_frame,
                list(evaluation_frame.columns),
            )
            outputs[f"{prefix}_evaluation_summary"] = _write_json(
                root / f"{prefix}_zhu_walkline_evaluation_summary.json",
                evaluation_summary,
            )

    if result.web_research_used:
        outputs["concept_suggestions"] = _write_text(
            root / "concept_stock_map_suggestions.md",
            "# Concept Stock Map Suggestions\n\n"
            "本次未自動覆蓋 `config/concept_stock_map.yaml`。\n\n"
            "若官方或可靠資料補到新的概念股歸屬，請人工確認後再更新 config。\n",
        )
    return outputs


def _summary_payload(result: ZhuWalklineResult, quality: DataQualityReport) -> dict[str, Any]:
    return {
        "asof_date": result.asof_date,
        "mode": result.mode,
        "formal_champion_changed": result.formal_champion_changed,
        "formal_trade_effect": result.formal_trade_effect,
        "web_research_used": result.web_research_used,
        "web_research_is_supplementary": result.web_research_is_supplementary,
        "data_sources": quality.used_tables,
        "data_quality": quality.to_dict(),
        "market": result.market,
        "sector_rotation": _records(result.sector_rotation.head(30)),
        "concept_rotation": _records(result.concept_rotation.head(30)),
        "top_bullish_watchlist": _candidate_records(result.top_bullish_watchlist),
        "top_rise_candidates": _candidate_records(result.top_rise_candidates),
        "top_fall_risks": _risk_records(result.top_fall_risks),
        "shadow_log_columns": SHADOW_LOG_COLUMNS,
        "run_notes": result.run_notes,
    }


def _candidate_records(frame: pd.DataFrame) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for _, row in frame.iterrows():
        rows.append(
            {
                "stock_id": row["stock_id"],
                "stock_name": _text(row.get("stock_name", "")),
                "close": _float(row.get("close")),
                "rise_score": _float(row.get("rise_score")),
                "grade": _text(row.get("grade", "")),
                "signal_stage": _text(row.get("signal_stage", "")),
                "trigger_type": _text(row.get("trigger_type", "")),
                "buy_observation_type": _text(row.get("buy_observation_type", "")),
                "buy_observation_detail_types": _text(row.get("buy_observation_detail_types", "")),
                "buy_trigger_price": _float(row.get("buy_trigger_price")),
                "buy_trigger_price_role": _text(row.get("buy_trigger_price_role", "")),
                "target_resistance_1": _float(row.get("target_resistance_1")),
                "target_resistance_2": _float(row.get("target_resistance_2")),
                "sell_warning_type": _text(row.get("sell_warning_type", "")),
                "sell_warning_detail_types": _text(row.get("sell_warning_detail_types", "")),
                "invalidation_price": _float(row.get("invalidation_price")),
                "invalid_price": _float(row.get("invalid_price")),
                "confirm_price": _float(row.get("confirm_price")),
                "failure_type": _text(row.get("failure_type", "")),
                "reversal_state": _text(row.get("reversal_state", "")),
                "sector": _text(row.get("sector", "")),
                "concepts": _as_list(row.get("concepts")),
                "trend_state": _text(row.get("trend_state", "")),
                "ma_state": _text(row.get("ma_state", "")),
                "kline_state": _text(row.get("kline_state", "")),
                "volume_state": _text(row.get("volume_state", "")),
                "institutional_score": _float(row.get("institutional_score")),
                "big_holder_score": _float(row.get("big_holder_score")),
                "margin_score": _float(row.get("margin_score")),
                "web_event_score": _float(row.get("web_event_score")),
                "support": [v for v in [row.get("support_1"), row.get("support_2")] if not _is_missing(v)],
                "resistance": [
                    v
                    for v in [row.get("resistance_1"), row.get("resistance_2")]
                    if not _is_missing(v)
                ],
                "support_zones": _zone_records(row, "support"),
                "resistance_zones": _zone_records(row, "resistance"),
                "support_zone_failed_today": bool(row.get("support_zone_failed_today", False)),
                "resistance_zone_breakout_today": bool(
                    row.get("resistance_zone_breakout_today", False)
                ),
                "entry_observation": _text(row.get("entry_observation", "")),
                "stop_reference": _text(row.get("stop_reference", "")),
                "reason": _as_list(row.get("reason")),
            }
        )
    return rows


def _risk_records(frame: pd.DataFrame) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for _, row in frame.iterrows():
        rows.append(
            {
                "stock_id": row["stock_id"],
                "stock_name": _text(row.get("stock_name", "")),
                "close": _float(row.get("close")),
                "fall_risk_score": _float(row.get("fall_risk_score")),
                "risk_grade": _text(row.get("risk_grade", "")),
                "signal_stage": _text(row.get("signal_stage", "")),
                "failure_type": _text(row.get("failure_type", "")),
                "sell_warning_type": _text(row.get("sell_warning_type", "")),
                "sell_warning_detail_types": _text(row.get("sell_warning_detail_types", "")),
                "invalidation_price": _float(row.get("invalidation_price")),
                "invalid_price": _float(row.get("invalid_price")),
                "stop_reference": _text(row.get("stop_reference", "")),
                "sector": _text(row.get("sector", "")),
                "concepts": _as_list(row.get("concepts")),
                "trend_break_reason": _text(row.get("trend_break_reason", "")),
                "ma_break_reason": _text(row.get("ma_break_reason", "")),
                "kline_weakness": _text(row.get("kline_weakness", "")),
                "volume_distribution": _text(row.get("volume_distribution", "")),
                "institutional_selling": _text(row.get("institutional_selling", "")),
                "margin_risk": _text(row.get("margin_risk", "")),
                "web_event_risk_score": _float(row.get("web_event_risk_score")),
                "support_broken": _as_list(row.get("support_broken")),
                "next_support": _as_list(row.get("next_support")),
                "support_zones": _zone_records(row, "support"),
                "broken_support_zone": _zone_record_from_prefix(row, "broken_support_zone"),
                "support_zone_failed_today": bool(row.get("support_zone_failed_today", False)),
                "reason": _as_list(row.get("risk_reason")),
            }
        )
    return rows


def _zone_records(row: pd.Series, side: str) -> list[dict[str, Any]]:
    return [
        record
        for idx in range(1, 4)
        if (record := _zone_record_from_prefix(row, f"{side}_zone_{idx}")) is not None
    ]


def _zone_record_from_prefix(row: pd.Series, prefix: str) -> dict[str, Any] | None:
    low = row.get(f"{prefix}_low")
    high = row.get(f"{prefix}_high")
    if _is_missing(low) or _is_missing(high):
        return None
    return {
        "low": _float(low),
        "high": _float(high),
        "label": _zone_text(row, prefix),
        "sources": _text(row.get(f"{prefix}_sources", "")),
    }


def _zone_text(row: pd.Series, prefix: str) -> str:
    label = row.get(f"{prefix}_label")
    if _text(label):
        return _text(label)
    low = row.get(f"{prefix}_low")
    high = row.get(f"{prefix}_high")
    if _is_missing(low) or _is_missing(high):
        return ""
    low_float = float(low)
    high_float = float(high)
    if abs(low_float - high_float) <= 1e-8:
        return f"{low_float:.2f}"
    return f"{low_float:.2f}～{high_float:.2f}"


def _market_report(result: ZhuWalklineResult, quality: DataQualityReport) -> str:
    rise_preview = result.top_bullish_watchlist.head(10)
    fall_preview = result.top_fall_risks.head(10)
    lines = [
        f"# {result.asof_date} 走圖／走線 shadow 全市場報告",
        "",
        "同學，走圖第一步不是問會不會漲，是先看趨勢。",
        "",
        "## 一、大盤狀態",
        "",
        f"- 狀態：{result.market['market_state']}",
        f"- 多方分數：{result.market['market_score']}",
        f"- 風險分數：{result.market['market_risk_score']}",
        f"- 來源：{result.market.get('source', '')}",
        "",
        "## 二、類股輪動",
        "",
        _markdown_table(
            result.sector_rotation.head(15),
            ["sector", "sector_rotation_rank", "sector_strength_score", "sector_risk_score", "sector_state"],
        ),
        "",
        "## 三、概念股輪動",
        "",
        "同學，概念股不是每一檔都會漲，要看領頭羊有沒有續強，落後股有沒有補漲，還有整個族群是不是同步站上均線。",
        "",
        _markdown_table(
            result.concept_rotation.head(15),
            ["concept", "concept_rotation_rank", "concept_strength_score", "concept_risk_score", "concept_leader_stock"],
        ),
        "",
        "## 四、多方轉強觀察股",
        "",
        "不是買進名單，不是明日必漲股。走圖不是預言，走圖是等訊號。",
        "不是買進名單，不是賣出指令，僅為支撐壓力觀察價與訊號失效價。",
        "",
        _markdown_table(
            rise_preview,
            [
                "stock_id",
                "stock_name",
                "close",
                "rise_score",
                "grade",
                "signal_stage",
                "trigger_type",
                "buy_observation_type",
                "buy_observation_detail_types",
                "buy_trigger_price",
                "buy_trigger_price_role",
                "sell_warning_type",
                "sell_warning_detail_types",
                "failure_type",
            ],
        ),
        "",
        "## 五、可能即將下跌風險名單",
        "",
        _markdown_table(
            fall_preview,
            [
                "stock_id",
                "stock_name",
                "close",
                "fall_risk_score",
                "risk_grade",
                "sell_warning_type",
                "sell_warning_detail_types",
                "stop_reference",
                "risk_reason_summary",
            ],
        ),
        "",
        "## 六、資料品質提醒",
        "",
        *[f"- {warning}" for warning in quality.warnings],
        "",
        _fixed_statement(result),
    ]
    return "\n".join(lines)


def _stock_report(result: ZhuWalklineResult) -> str:
    if not result.top_bullish_watchlist.empty:
        row = result.top_bullish_watchlist.iloc[0]
    elif not result.top_fall_risks.empty:
        row = result.top_fall_risks.iloc[0]
    else:
        row = result.feature_matrix.iloc[0]
    web_section = (
        "本次網路資料僅作為題材與事件補充，核心評分仍以本地量價、均線、法人、融資券資料為主。"
        if result.web_research_used
        else "本次分析未使用網路補充資料，僅依本地資料庫計算。"
    )
    buy_trigger_role = _text(row.get("buy_trigger_price_role", ""))
    if buy_trigger_role == "NEXT_CONFIRMATION_PRICE":
        buy_trigger_role_note = "NEXT_CONFIRMATION_PRICE（尚未觸發，這是下一個確認觀察價，不是買進價）"
    elif buy_trigger_role == "TRIGGERED_PRICE":
        buy_trigger_role_note = "TRIGGERED_PRICE（已觸發的支撐壓力觀察價，仍不是買進指令）"
    else:
        buy_trigger_role_note = "EMPTY（尚無可用觀察價）"
    lines = [
        f"# {row['stock_id']} {row.get('stock_name', '')}｜走圖分析",
        "",
        "## 一、先講結論",
        "",
        "同學，這張圖現在是：",
        "",
        f"- 趨勢：{row.get('trend_state', '')}",
        f"- 均線：{row.get('ma_state', '')}",
        f"- K棒：{row.get('kline_state', '')}",
        f"- 量能：{row.get('volume_state', '')}",
        f"- 法人：5日外資 {row.get('foreign_5d', 0):,.0f}，投信 {row.get('investment_trust_5d', 0):,.0f}",
        f"- 大戶／主力：{row.get('big_holder_data_source', 'proxy')} score={row.get('big_holder_score', 0):.1f}",
        f"- 融資券：margin_score={row.get('margin_score', 0):.1f}，risk={row.get('margin_risk_score', 0):.1f}",
        f"- 大盤背景：{row.get('market_state', '')}",
        f"- 類股輪動：{row.get('sector', '')} rank={row.get('sector_rotation_rank', '')}",
        f"- 概念股輪動：{', '.join(_as_list(row.get('concepts')))}",
        f"- 訊號階段：{row.get('signal_stage', '')}",
        f"- 觸發型態：{row.get('trigger_type', '')}",
        f"- 買點觀察型態：{_text(row.get('buy_observation_type', ''))}",
        f"- 買點觀察明細：{_text(row.get('buy_observation_detail_types', ''))}",
        f"- 買點觀察價：{_format_price(row.get('buy_trigger_price'))}",
        f"- 買點觀察價角色：{buy_trigger_role_note}",
        f"- 賣點警示型態：{_text(row.get('sell_warning_type', ''))}",
        f"- 賣點警示明細：{_text(row.get('sell_warning_detail_types', ''))}",
        f"- 失敗型態：{_text(row.get('failure_type', ''))}",
        f"- 結論：rise_score={row.get('rise_score', 0):.1f}，fall_risk_score={row.get('fall_risk_score', 0):.1f}",
        "",
        "## 二、趨勢",
        "",
        f"同學，趨勢狀態是 `{row.get('trend_state', '')}`。頭頭高／底底高與20日、60日位置要一起看。",
        "",
        "## 三、均線",
        "",
        f"5日 {row.get('ma5', np.nan):.2f}、10日 {row.get('ma10', np.nan):.2f}、20日 {row.get('ma20', np.nan):.2f}、60日 {row.get('ma60', np.nan):.2f}。",
        "",
        "## 四、K線",
        "",
        f"今日K棒判定為 `{row.get('kline_state', '')}`。同學，有下影線不等於轉強，收過壓力才叫轉強。",
        "",
        "## 五、量能",
        "",
        f"量能狀態為 `{row.get('volume_state', '')}`，20日量比 {row.get('vol_ratio_20', np.nan):.2f}。",
        "",
        "## 六、法人籌碼",
        "",
        f"法人分數 {row.get('institutional_score', 0):.1f}，法人賣壓分數 {row.get('institutional_selling_score', 0):.1f}。",
        "",
        "## 七、大戶／主力代理",
        "",
        f"大戶/主力資料來源 `{row.get('big_holder_data_source', '')}`，分數 {row.get('big_holder_score', 0):.1f}。",
        "",
        "## 八、融資券",
        "",
        f"融資 score={row.get('margin_score', 0):.1f}，融資風險={row.get('margin_risk_score', 0):.1f}。",
        "",
        "## 九、大盤與類股背景",
        "",
        f"大盤 `{row.get('market_state', '')}`，類股 `{row.get('sector', '')}`。",
        "",
        "## 十、支撐與壓力",
        "",
        "| 價位 | 意義 |",
        "|---:|---|",
        f"| {_zone_text(row, 'support_zone_1')} | 支撐區1 |",
        f"| {_zone_text(row, 'support_zone_2')} | 支撐區2 |",
        f"| {_zone_text(row, 'resistance_zone_1')} | 壓力區1 |",
        f"| {_zone_text(row, 'resistance_zone_2')} | 壓力區2 |",
        "",
        f"- 支撐有效：{bool(row.get('support_zone_holding_today', False))}",
        f"- 支撐失敗：{bool(row.get('support_zone_failed_today', False))}",
        f"- 壓力有效突破：{bool(row.get('resistance_zone_breakout_today', False))}",
        f"- 壓力突破失敗：{bool(row.get('resistance_zone_breakout_failed_today', False))}",
        f"- 目標壓力1：{_format_price(row.get('target_resistance_1'))}",
        f"- 目標壓力2：{_format_price(row.get('target_resistance_2'))}",
        f"- 訊號失敗價：{_format_price(row.get('invalidation_price'))}",
        "",
        "## 十一、明日劇本",
        "",
        "### 劇本A：轉強",
        "",
        f"條件：收盤站上壓力區 {_zone_text(row, 'resistance_zone_1')}，並維持量價同步。",
        "",
        "### 劇本B：續弱",
        "",
        f"條件：跌破支撐區 {_zone_text(row, 'support_zone_1')}，且量能放大。",
        "",
        "### 劇本C：整理",
        "",
        "條件：沒有收過壓力，也沒有跌破支撐。同學，沒有訊號，就沒有動作。",
        "",
        "## 十二、未持有者",
        "",
        "不是買進名單，不是賣出指令，僅為支撐壓力觀察價與訊號失效價。",
        "",
        f"同學，未持有不要急。{row.get('non_holder_observation', row.get('entry_observation', ''))}",
        "",
        f"- 觀察型態：{_text(row.get('buy_observation_type', '')) or '尚未觸發'}",
        f"- 觀察明細：{_text(row.get('buy_observation_detail_types', ''))}",
        f"- 觀察價：{_format_price(row.get('buy_trigger_price'))}",
        f"- 觀察價角色：{buy_trigger_role_note}",
        f"- 確認價：{_format_price(row.get('confirm_price'))}",
        "- 不追價條件：沒有站上壓力就只是觀察。",
        "",
        "## 十三、已持有者",
        "",
        "不是買進名單，不是賣出指令，僅為支撐壓力觀察價與訊號失效價。",
        "",
        f"同學，已持有先看防守點。{row.get('holder_discipline', row.get('stop_reference', ''))}",
        "",
        f"- 防守價：{_format_price(row.get('invalidation_price', row.get('invalid_price')))}",
        f"- 賣點警示：{_text(row.get('sell_warning_type', '')) or '尚未觸發'}",
        f"- 賣點警示明細：{_text(row.get('sell_warning_detail_types', ''))}",
        "- 續強觀察條件：站穩確認價且沒有放量上影。",
        "- 風險升高觀察條件：跌破短均線或出現高檔供給。",
        "- 訊號失效觀察條件：跌破防守價收不回。",
        "",
        "## 十四、網路補充資料",
        "",
        web_section,
        "",
        "## 十五、一句話",
        "",
        "同學，空手不是沒有操作，空手是在等勝率。",
        "",
        _fixed_statement(result),
    ]
    return "\n".join(lines)


def _data_quality_report(quality: DataQualityReport, result: ZhuWalklineResult) -> str:
    lines = [
        f"# {result.asof_date} Zhu Walkline Data Quality",
        "",
        "## SQLite tables",
        "",
        *[f"- {table}" for table in quality.used_tables],
        "",
        "## Local files scanned",
        "",
        *([f"- {path}" for path in quality.scanned_files[:80]] or ["- none"]),
        "",
        "## Used fields",
        "",
        *[f"- {table}: {', '.join(fields)}" for table, fields in quality.used_fields.items()],
        "",
        "## Missing tables / fields",
        "",
        *([f"- table: {table}" for table in quality.missing_tables] or ["- none"]),
        "",
        f"- 最新股價日期：{quality.latest_price_date}",
        f"- 最新法人日期：{quality.latest_chip_date}",
        f"- 最新融資券日期：{quality.latest_margin_date}",
        f"- 最新大戶資料日期：{quality.latest_big_holder_date}",
        f"- 最新概念股 mapping 日期：{quality.concept_map_date}",
        f"- 是否啟用網路搜尋：{result.web_research_used}",
        f"- 網路搜尋來源筆數：{len(result.web_records)}",
        "",
        "## No-lookahead filters",
        "",
        *[f"- {item}" for item in quality.no_lookahead_filters],
        "",
        "## Warnings",
        "",
        *([f"- {warning}" for warning in quality.warnings] or ["- none"]),
        "",
        _fixed_statement(result),
    ]
    return "\n".join(lines)


def _shadow_log_frame(feature_matrix: pd.DataFrame) -> pd.DataFrame:
    output = feature_matrix.copy()
    for column in SHADOW_LOG_COLUMNS:
        if column not in output.columns:
            output[column] = ""
    output = output[SHADOW_LOG_COLUMNS].sort_values(
        ["failure_type", "fall_risk_score", "rise_score"],
        ascending=[False, False, False],
    )
    return output.map(_clean_output_value)


def _fixed_statement(result: ZhuWalklineResult) -> str:
    return "\n".join(
        [
            "本報告為技術分析教育與 shadow observation，不是投資建議，不是買賣指令。",
            f"mode={result.mode}",
            f"formal_champion_changed={result.formal_champion_changed}",
            f"formal_trade_effect={result.formal_trade_effect}",
            f"web_research_used={result.web_research_used}",
            f"web_research_is_supplementary={result.web_research_is_supplementary}",
        ]
    )


def _write_json(path: Path, payload: dict[str, Any]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True, default=_json_default),
        encoding="utf-8",
    )
    return path


def _write_csv(path: Path, frame: pd.DataFrame, columns: list[str]) -> Path:
    output = frame.copy()
    for column in columns:
        if column not in output.columns:
            output[column] = ""
    output = output[columns].copy()
    for column in output.columns:
        if output[column].map(lambda value: isinstance(value, list)).any():
            output[column] = output[column].map(
                lambda value: "|".join(_text(item) for item in value if _text(item))
                if isinstance(value, list)
                else value
            )
        output[column] = output[column].map(_clean_output_value)
    output.to_csv(path, index=False, encoding="utf-8-sig")
    return path


def _write_text(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def _markdown_table(frame: pd.DataFrame, columns: list[str]) -> str:
    if frame.empty:
        return "_no rows_"
    output = frame.copy()
    for column in columns:
        if column not in output.columns:
            output[column] = ""
    output = output[columns].head(30).copy()
    for column in output.columns:
        output[column] = output[column].map(_format_cell)
    header = "| " + " | ".join(columns) + " |"
    divider = "| " + " | ".join(["---"] * len(columns)) + " |"
    rows = ["| " + " | ".join(str(value) for value in row) + " |" for row in output.to_numpy()]
    return "\n".join([header, divider, *rows])


def _format_cell(value: Any) -> str:
    if _is_missing(value):
        return ""
    if isinstance(value, list):
        return ", ".join(_text(item) for item in value if _text(item))
    if isinstance(value, float):
        return f"{value:.4g}"
    return _text(value).replace("\n", " ")


def _format_price(value: Any) -> str:
    number = _float(value)
    return "" if number is None else f"{number:.2f}"


def _records(frame: pd.DataFrame) -> list[dict[str, Any]]:
    return json.loads(json.dumps(frame.to_dict(orient="records"), default=_json_default, ensure_ascii=False))


def _as_list(value: Any) -> list[Any]:
    if isinstance(value, list):
        return [_clean_output_value(item) for item in value if not _is_missing(item)]
    if _is_missing(value):
        return []
    return [value]


def _float(value: Any) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if not np.isfinite(number):
        return None
    return number


def _text(value: Any) -> str:
    if _is_missing(value):
        return ""
    text = str(value).strip()
    if text.lower() in {"nan", "none", "<na>"}:
        return ""
    return text


def _is_missing(value: Any) -> bool:
    if value is None:
        return True
    try:
        missing = pd.isna(value)
    except (TypeError, ValueError):
        return False
    if isinstance(missing, (bool, np.bool_)):
        return bool(missing)
    return False


def _clean_output_value(value: Any) -> Any:
    if _is_missing(value):
        return ""
    if isinstance(value, str):
        return _text(value)
    return value


def _json_default(value: Any) -> Any:
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating,)):
        number = float(value)
        return None if not np.isfinite(number) else number
    if isinstance(value, (np.bool_,)):
        return bool(value)
    if isinstance(value, pd.Timestamp):
        return value.date().isoformat()
    if isinstance(value, Path):
        return str(value)
    if _is_missing(value):
        return None
    raise TypeError(f"Object is not JSON serializable: {type(value)!r}")
