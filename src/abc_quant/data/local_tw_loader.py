"""Local Taiwan market data loader for the Zhu walkline shadow scanner."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
import sqlite3
from typing import Any

import pandas as pd


@dataclass(frozen=True)
class DataQualityReport:
    """Structured data-quality notes emitted with every scanner run."""

    sqlite_path: str
    sqlite_exists: bool
    found_sqlite_tables: list[str] = field(default_factory=list)
    used_tables: list[str] = field(default_factory=list)
    missing_tables: list[str] = field(default_factory=list)
    scanned_files: list[str] = field(default_factory=list)
    used_fields: dict[str, list[str]] = field(default_factory=dict)
    missing_fields: dict[str, list[str]] = field(default_factory=dict)
    latest_price_date: str | None = None
    latest_chip_date: str | None = None
    latest_margin_date: str | None = None
    latest_big_holder_date: str | None = None
    latest_market_index_date: str | None = None
    latest_sector_rotation_date: str | None = None
    concept_map_date: str | None = None
    warnings: list[str] = field(default_factory=list)
    no_lookahead_filters: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "missing_tables": self.missing_tables,
            "missing_fields": self.missing_fields,
            "latest_price_date": self.latest_price_date,
            "latest_chip_date": self.latest_chip_date,
            "latest_margin_date": self.latest_margin_date,
            "latest_big_holder_date": self.latest_big_holder_date,
            "warnings": self.warnings,
        }


@dataclass(frozen=True)
class LocalTwDataBundle:
    """All local frames needed by the scanner."""

    asof_date: str
    requested_asof: str
    price_history: pd.DataFrame
    stock_info: pd.DataFrame
    chip_history: pd.DataFrame
    margin_history: pd.DataFrame
    holder_latest: pd.DataFrame
    market_history: pd.DataFrame
    sector_sentiment: pd.DataFrame
    stock_context: pd.DataFrame
    class_membership: pd.DataFrame
    data_quality: DataQualityReport


def load_local_tw_bundle(
    config: dict[str, Any],
    *,
    asof: str,
    stock_id: str | None = None,
) -> LocalTwDataBundle:
    """Load local Taiwan stock data from SQLite and optional FinLab files.

    The loader never reads rows after ``asof``. If ``asof`` is ``latest``, it
    resolves to the latest available local price date.
    """
    data_config = config.get("data", {})
    runtime_config = config.get("runtime", {})
    sqlite_path = Path(data_config.get("sqlite_path", ""))
    finlab_root = Path(data_config.get("finlab_items_root", ""))
    lookback_days = int(runtime_config.get("lookback_calendar_days", 420))
    requested_asof = asof

    warnings: list[str] = []
    missing_tables: list[str] = []
    used_tables: list[str] = []
    used_fields: dict[str, list[str]] = {}
    missing_fields: dict[str, list[str]] = {}
    no_lookahead_filters = [
        "price rows filtered by date <= asof_date before feature computation",
        "chip rows filtered by trade_date <= asof_date",
        "margin rows filtered by trade_date <= asof_date",
        "holder and sector snapshots selected with snapshot date <= asof_date",
    ]

    if not sqlite_path.exists():
        quality = DataQualityReport(
            sqlite_path=str(sqlite_path),
            sqlite_exists=False,
            missing_tables=["daily_ohlcv_features"],
            scanned_files=_scan_finlab_files(finlab_root),
            warnings=[f"SQLite database not found: {sqlite_path}"],
            no_lookahead_filters=no_lookahead_filters,
        )
        raise FileNotFoundError(f"SQLite database not found: {sqlite_path}")

    with sqlite3.connect(sqlite_path) as connection:
        tables = _list_tables(connection)
        asof_date = _resolve_asof_date(connection, asof)
        stock_id = _normalize_stock_id(stock_id) if stock_id else None

        stock_info = _load_stock_info(connection, tables, used_tables, missing_tables, used_fields)
        price_history = _load_price_history(
            connection,
            tables,
            asof_date=asof_date,
            lookback_days=lookback_days,
            stock_id=stock_id,
            used_tables=used_tables,
            missing_tables=missing_tables,
            used_fields=used_fields,
        )
        if not price_history.empty and not stock_info.empty and stock_id is None:
            allowed = set(stock_info["stock_id"].astype(str))
            filtered = price_history[price_history["stock_id"].isin(allowed)].copy()
            if not filtered.empty:
                price_history = filtered

        if price_history.empty:
            raise ValueError(f"No local price rows available at or before {asof_date}")

        latest_price_date = _max_date(price_history, "date")
        if latest_price_date and latest_price_date < asof_date:
            warnings.append(
                f"latest price date {latest_price_date} is earlier than requested asof {asof_date}"
            )

        chip_history = _load_chip_history(
            connection,
            tables,
            asof_date=asof_date,
            stock_id=stock_id,
            used_tables=used_tables,
            missing_tables=missing_tables,
            used_fields=used_fields,
        )
        margin_history = _load_margin_history(
            connection,
            tables,
            asof_date=asof_date,
            stock_id=stock_id,
            used_tables=used_tables,
            missing_tables=missing_tables,
            used_fields=used_fields,
        )
        holder_latest = _load_snapshot_table(
            connection,
            tables,
            table_name="latest_tw_tdcc_holder_moving_averages",
            date_column="date",
            asof_date=asof_date,
            stock_id=stock_id,
            used_tables=used_tables,
            missing_tables=missing_tables,
            used_fields=used_fields,
        )
        market_history = _load_market_history(
            connection,
            tables,
            asof_date=asof_date,
            used_tables=used_tables,
            missing_tables=missing_tables,
            used_fields=used_fields,
        )
        sector_sentiment = _load_latest_by_date(
            connection,
            tables,
            table_name="industry_concept_sentiment_daily",
            fallback_table="latest_industry_concept_sentiment",
            date_column="date",
            asof_date=asof_date,
            used_tables=used_tables,
            missing_tables=missing_tables,
            used_fields=used_fields,
        )
        stock_context = _load_latest_by_date(
            connection,
            tables,
            table_name="latest_stock_industry_concept_sentiment_context",
            fallback_table=None,
            date_column="date",
            asof_date=asof_date,
            used_tables=used_tables,
            missing_tables=missing_tables,
            used_fields=used_fields,
        )
        class_membership = _load_class_membership(
            connection,
            tables,
            used_tables=used_tables,
            missing_tables=missing_tables,
            used_fields=used_fields,
        )

    if margin_history.empty:
        warnings.append("融資券資料缺失，本次 margin_score 使用 neutral，不納入加減分。")
    if holder_latest.empty:
        warnings.append("大戶資料缺失，本次 big_holder_score 使用主力代理 proxy，不視為真實大戶持股。")
    if market_history.empty:
        warnings.append("大盤正式指數資料缺失，本次 market_state 使用全市場等權 proxy。")

    latest_chip_date = _max_date(chip_history, "trade_date")
    latest_margin_date = _max_date(margin_history, "trade_date")
    latest_big_holder_date = _max_date(holder_latest, "date")
    latest_market_index_date = _max_date(market_history, "date")
    latest_sector_date = _max_date(sector_sentiment, "date")
    if latest_market_index_date and latest_price_date and latest_market_index_date < latest_price_date:
        warnings.append(
            "大盤正式指數均線資料較股價資料舊，market_state 會優先使用全市場 proxy。"
        )

    concept_path = Path("config/concept_stock_map.yaml")
    concept_map_date = (
        datetime.fromtimestamp(concept_path.stat().st_mtime).date().isoformat()
        if concept_path.exists()
        else None
    )
    quality = DataQualityReport(
        sqlite_path=str(sqlite_path),
        sqlite_exists=True,
        found_sqlite_tables=tables,
        used_tables=sorted(set(used_tables)),
        missing_tables=sorted(set(missing_tables)),
        scanned_files=_scan_finlab_files(finlab_root),
        used_fields=used_fields,
        missing_fields=missing_fields,
        latest_price_date=latest_price_date,
        latest_chip_date=latest_chip_date,
        latest_margin_date=latest_margin_date,
        latest_big_holder_date=latest_big_holder_date,
        latest_market_index_date=latest_market_index_date,
        latest_sector_rotation_date=latest_sector_date,
        concept_map_date=concept_map_date,
        warnings=warnings,
        no_lookahead_filters=no_lookahead_filters,
    )
    return LocalTwDataBundle(
        asof_date=asof_date,
        requested_asof=requested_asof,
        price_history=price_history,
        stock_info=stock_info,
        chip_history=chip_history,
        margin_history=margin_history,
        holder_latest=holder_latest,
        market_history=market_history,
        sector_sentiment=sector_sentiment,
        stock_context=stock_context,
        class_membership=class_membership,
        data_quality=quality,
    )


def load_future_price_rows(
    sqlite_path: str | Path,
    *,
    asof_date: str,
    stock_ids: list[str],
    horizon_calendar_days: int = 25,
) -> pd.DataFrame:
    """Load evaluator-only future price rows after ``asof_date``."""
    if not stock_ids:
        return pd.DataFrame()
    placeholders = ",".join("?" for _ in stock_ids)
    query = f"""
        select date, stock_id, close, high, low
        from daily_ohlcv_features
        where date > ?
          and date <= date(?, ?)
          and stock_id in ({placeholders})
        order by stock_id, date
    """
    params: list[Any] = [asof_date, asof_date, f"+{horizon_calendar_days} day", *stock_ids]
    with sqlite3.connect(sqlite_path) as connection:
        return pd.read_sql_query(query, connection, params=params, parse_dates=["date"])


def _list_tables(connection: sqlite3.Connection) -> list[str]:
    rows = connection.execute(
        "select name from sqlite_master where type='table' order by name"
    ).fetchall()
    return [str(row[0]) for row in rows]


def _table_exists(tables: list[str], table_name: str) -> bool:
    return table_name in set(tables)


def _resolve_asof_date(connection: sqlite3.Connection, asof: str) -> str:
    if asof == "latest":
        row = connection.execute("select max(date) from daily_ohlcv_features").fetchone()
        if row is None or row[0] is None:
            raise ValueError("Cannot resolve latest asof date from daily_ohlcv_features")
        return str(row[0])[:10]
    parsed = pd.to_datetime(asof, errors="raise").date()
    return parsed.isoformat()


def _load_stock_info(
    connection: sqlite3.Connection,
    tables: list[str],
    used_tables: list[str],
    missing_tables: list[str],
    used_fields: dict[str, list[str]],
) -> pd.DataFrame:
    frames: list[pd.DataFrame] = []
    if _table_exists(tables, "bigrich_industry_map"):
        query = """
            select stock_code as stock_id,
                   stock_name,
                   coalesce(industry_name, industry) as sector,
                   market
            from bigrich_industry_map
        """
        frame = pd.read_sql_query(query, connection)
        frame["source_priority"] = 1
        frames.append(frame)
        used_tables.append("bigrich_industry_map")
        used_fields["bigrich_industry_map"] = ["stock_code", "stock_name", "industry_name", "market"]
    else:
        missing_tables.append("bigrich_industry_map")

    if _table_exists(tables, "official_twse_company_basic"):
        query = """
            select 公司代號 as stock_id,
                   公司簡稱 as stock_name,
                   產業別 as sector,
                   'TWSE' as market
            from official_twse_company_basic
        """
        frame = pd.read_sql_query(query, connection)
        frame["source_priority"] = 2
        frames.append(frame)
        used_tables.append("official_twse_company_basic")
        used_fields["official_twse_company_basic"] = ["公司代號", "公司簡稱", "產業別"]

    if _table_exists(tables, "official_tpex_company_basic"):
        query = """
            select SecuritiesCompanyCode as stock_id,
                   CompanyAbbreviation as stock_name,
                   SecuritiesIndustryCode as sector,
                   'TPEx' as market
            from official_tpex_company_basic
        """
        frame = pd.read_sql_query(query, connection)
        frame["source_priority"] = 3
        frames.append(frame)
        used_tables.append("official_tpex_company_basic")
        used_fields["official_tpex_company_basic"] = [
            "SecuritiesCompanyCode",
            "CompanyAbbreviation",
            "SecuritiesIndustryCode",
        ]

    if not frames:
        return pd.DataFrame(columns=["stock_id", "stock_name", "sector", "market"])
    combined = pd.concat(frames, ignore_index=True)
    combined["stock_id"] = combined["stock_id"].map(_normalize_stock_id)
    combined = combined[combined["stock_id"].str.len() == 4].copy()
    combined = combined.sort_values(["stock_id", "source_priority"]).drop_duplicates("stock_id")
    return combined[["stock_id", "stock_name", "sector", "market"]].reset_index(drop=True)


def _load_price_history(
    connection: sqlite3.Connection,
    tables: list[str],
    *,
    asof_date: str,
    lookback_days: int,
    stock_id: str | None,
    used_tables: list[str],
    missing_tables: list[str],
    used_fields: dict[str, list[str]],
) -> pd.DataFrame:
    table_name = "daily_ohlcv_features"
    if not _table_exists(tables, table_name):
        missing_tables.append(table_name)
        return pd.DataFrame()
    stock_clause = "and stock_id = ?" if stock_id else "and length(stock_id) = 4"
    params: list[Any] = [asof_date, asof_date, f"-{lookback_days} day"]
    if stock_id:
        params.append(stock_id)
    query = f"""
        select date, stock_id, open, high, low, close, volume
        from {table_name}
        where date <= ?
          and date >= date(?, ?)
          {stock_clause}
        order by stock_id, date
    """
    used_tables.append(table_name)
    used_fields[table_name] = ["date", "stock_id", "open", "high", "low", "close", "volume"]
    frame = pd.read_sql_query(query, connection, params=params, parse_dates=["date"])
    frame["stock_id"] = frame["stock_id"].astype(str)
    return frame


def _load_chip_history(
    connection: sqlite3.Connection,
    tables: list[str],
    *,
    asof_date: str,
    stock_id: str | None,
    used_tables: list[str],
    missing_tables: list[str],
    used_fields: dict[str, list[str]],
) -> pd.DataFrame:
    table_name = "tw_official_institutional_trading_daily"
    if not _table_exists(tables, table_name):
        missing_tables.append(table_name)
        return pd.DataFrame()
    stock_clause = "and stock_id = ?" if stock_id else ""
    params: list[Any] = [asof_date, asof_date, "-45 day"]
    if stock_id:
        params.append(stock_id)
    query = f"""
        select trade_date,
               stock_id,
               stock_name,
               foreign_net_buy_shares,
               trust_net_buy_shares,
               dealer_net_buy_shares,
               dealer_self_net_buy_shares,
               dealer_hedge_net_buy_shares,
               institutional_net_buy_shares
        from {table_name}
        where trade_date <= ?
          and trade_date >= date(?, ?)
          {stock_clause}
        order by stock_id, trade_date
    """
    used_tables.append(table_name)
    used_fields[table_name] = [
        "trade_date",
        "stock_id",
        "foreign_net_buy_shares",
        "trust_net_buy_shares",
        "dealer_net_buy_shares",
        "institutional_net_buy_shares",
    ]
    return pd.read_sql_query(query, connection, params=params, parse_dates=["trade_date"])


def _load_margin_history(
    connection: sqlite3.Connection,
    tables: list[str],
    *,
    asof_date: str,
    stock_id: str | None,
    used_tables: list[str],
    missing_tables: list[str],
    used_fields: dict[str, list[str]],
) -> pd.DataFrame:
    table_name = "tw_margin_balance_history"
    if not _table_exists(tables, table_name):
        missing_tables.append(table_name)
        return pd.DataFrame()
    stock_clause = "and stock_id = ?" if stock_id else ""
    params: list[Any] = [asof_date, asof_date, "-45 day"]
    if stock_id:
        params.append(stock_id)
    query = f"""
        select trade_date, stock_id, margin_balance
        from {table_name}
        where trade_date <= ?
          and trade_date >= date(?, ?)
          {stock_clause}
        order by stock_id, trade_date
    """
    used_tables.append(table_name)
    used_fields[table_name] = ["trade_date", "stock_id", "margin_balance"]
    return pd.read_sql_query(query, connection, params=params, parse_dates=["trade_date"])


def _load_snapshot_table(
    connection: sqlite3.Connection,
    tables: list[str],
    *,
    table_name: str,
    date_column: str,
    asof_date: str,
    stock_id: str | None,
    used_tables: list[str],
    missing_tables: list[str],
    used_fields: dict[str, list[str]],
) -> pd.DataFrame:
    if not _table_exists(tables, table_name):
        missing_tables.append(table_name)
        return pd.DataFrame()
    row = connection.execute(
        f"select max({date_column}) from {table_name} where {date_column} <= ?",
        (asof_date,),
    ).fetchone()
    snapshot_date = row[0] if row else None
    if snapshot_date is None:
        return pd.DataFrame()
    stock_clause = "and stock_id = ?" if stock_id else ""
    params: list[Any] = [snapshot_date]
    if stock_id:
        params.append(stock_id)
    query = f"select * from {table_name} where {date_column} = ? {stock_clause}"
    frame = pd.read_sql_query(query, connection, params=params, parse_dates=[date_column])
    used_tables.append(table_name)
    used_fields[table_name] = list(frame.columns)
    return frame


def _load_market_history(
    connection: sqlite3.Connection,
    tables: list[str],
    *,
    asof_date: str,
    used_tables: list[str],
    missing_tables: list[str],
    used_fields: dict[str, list[str]],
) -> pd.DataFrame:
    table_name = "tw_market_index_moving_averages_daily"
    if not _table_exists(tables, table_name):
        missing_tables.append(table_name)
        return pd.DataFrame()
    query = f"""
        select date, index_id, index_name, open, high, low, close, ma5, ma20, ma60, ma120
        from {table_name}
        where date <= ?
          and date >= date(?, '-420 day')
        order by index_id, date
    """
    used_tables.append(table_name)
    used_fields[table_name] = ["date", "index_id", "index_name", "open", "high", "low", "close"]
    return pd.read_sql_query(query, connection, params=[asof_date, asof_date], parse_dates=["date"])


def _load_latest_by_date(
    connection: sqlite3.Connection,
    tables: list[str],
    *,
    table_name: str,
    fallback_table: str | None,
    date_column: str,
    asof_date: str,
    used_tables: list[str],
    missing_tables: list[str],
    used_fields: dict[str, list[str]],
) -> pd.DataFrame:
    source_table = table_name if _table_exists(tables, table_name) else fallback_table
    if source_table is None or not _table_exists(tables, source_table):
        missing_tables.append(table_name)
        return pd.DataFrame()
    row = connection.execute(
        f"select max({date_column}) from {source_table} where {date_column} <= ?",
        (asof_date,),
    ).fetchone()
    snapshot_date = row[0] if row else None
    if snapshot_date is None:
        return pd.DataFrame()
    frame = pd.read_sql_query(
        f"select * from {source_table} where {date_column} = ?",
        connection,
        params=[snapshot_date],
        parse_dates=[date_column],
    )
    used_tables.append(source_table)
    used_fields[source_table] = list(frame.columns)
    return frame


def _load_class_membership(
    connection: sqlite3.Connection,
    tables: list[str],
    *,
    used_tables: list[str],
    missing_tables: list[str],
    used_fields: dict[str, list[str]],
) -> pd.DataFrame:
    table_name = "class_membership"
    if not _table_exists(tables, table_name):
        missing_tables.append(table_name)
        return pd.DataFrame()
    fields = [
        "group_key",
        "group_label",
        "category_name",
        "category_display",
        "exchange",
        "stock_id",
    ]
    query = "select " + ", ".join(fields) + f" from {table_name}"
    frame = pd.read_sql_query(query, connection)
    used_tables.append(table_name)
    used_fields[table_name] = fields
    frame["stock_id"] = frame["stock_id"].map(_normalize_stock_id)
    return frame


def _scan_finlab_files(root: Path, *, limit: int = 80) -> list[str]:
    if not root.exists():
        return []
    matches: list[str] = []
    suffixes = {".pkl", ".pickle", ".parquet", ".csv"}
    for path in root.rglob("*"):
        if path.is_file() and path.suffix.lower() in suffixes:
            matches.append(str(path))
            if len(matches) >= limit:
                break
    return matches


def _max_date(frame: pd.DataFrame, column: str) -> str | None:
    if frame.empty or column not in frame.columns:
        return None
    value = pd.to_datetime(frame[column], errors="coerce").max()
    if pd.isna(value):
        return None
    return value.date().isoformat()


def _normalize_stock_id(value: object) -> str:
    if value is None:
        return ""
    text = str(value).strip()
    digits = "".join(ch for ch in text if ch.isdigit())
    if len(digits) >= 4:
        return digits[:4]
    return digits.zfill(4) if digits else ""
