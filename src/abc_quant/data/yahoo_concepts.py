"""Yahoo Taiwan concept membership snapshots for shadow research.

The downloader treats each Yahoo concept page as a versioned source snapshot.
Snapshots are append-only: a repeated content hash is idempotent, while changed
content creates a new snapshot id even when Yahoo reports the same market date.
"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from datetime import datetime
import hashlib
import html
import json
from pathlib import Path
import re
import sqlite3
import time
from typing import Any, Callable
from urllib.parse import parse_qs, quote, urlencode, urljoin, urlparse
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo

import pandas as pd


YAHOO_CLASS_URL = "https://tw.stock.yahoo.com/class"
YAHOO_CATEGORY_LABEL = "概念股"
IMPORTANT_BASELINE = "IMPORTANT_BASELINE"
POINT_IN_TIME_SNAPSHOT = "point_in_time_snapshot"
STATIC_CURRENT_BACKFILL = "static_current_backfill_user_authorized"

_CONCEPT_LINK_RE = re.compile(r'<a[^>]+href="(?P<href>[^"]+)"[^>]*>(?P<label>.*?)</a>', re.I | re.S)
_TAG_RE = re.compile(r"<[^>]+>")
_YAHOO_SYMBOL_RE = re.compile(r"^(?P<stock_id>\d{4,6})\.(?P<market>TW|TWO)$")


@dataclass(frozen=True)
class YahooConceptCategory:
    concept_name: str
    source_url: str


@dataclass(frozen=True)
class YahooConceptSnapshot:
    manifest: dict[str, Any]
    categories: pd.DataFrame
    membership: pd.DataFrame


def parse_concept_categories(page_html: str, *, base_url: str = YAHOO_CLASS_URL) -> list[YahooConceptCategory]:
    """Extract the Yahoo concept layer and ignore other class-page sections."""

    categories: dict[str, YahooConceptCategory] = {}
    for match in _CONCEPT_LINK_RE.finditer(page_html):
        href = html.unescape(match.group("href"))
        absolute_url = urljoin(base_url, href)
        query = parse_qs(urlparse(absolute_url).query)
        if query.get("categoryLabel", [""])[0] != YAHOO_CATEGORY_LABEL:
            continue
        concept_name = query.get("category", [""])[0].strip()
        if not concept_name:
            concept_name = html.unescape(_TAG_RE.sub(" ", match.group("label"))).strip()
        if concept_name and concept_name not in categories:
            categories[concept_name] = YahooConceptCategory(concept_name, absolute_url)
    return list(categories.values())


def build_class_quotes_api_url(concept_name: str, *, offset: int = 0) -> str:
    """Build Yahoo's paginated class-quotes resource URL."""

    resource_params = {
        "category": concept_name,
        "categoryLabel": YAHOO_CATEGORY_LABEL,
        "categoryName": concept_name,
        "offset": str(int(offset)),
    }
    resource_path = ";".join(
        f"{key}={quote(value, safe='')}" for key, value in resource_params.items()
    )
    query = urlencode(
        {
            "bkt": "",
            "device": "desktop",
            "ecma": "modern",
            "feature": "ecmaModern",
            "intl": "tw",
            "lang": "zh-Hant-TW",
            "partner": "none",
            "region": "TW",
            "site": "finance",
            "tz": "Asia/Taipei",
            "returnMeta": "true",
        }
    )
    return (
        "https://tw.stock.yahoo.com/_td-stock/api/resource/"
        f"StockServices.getClassQuotes;{resource_path}?{query}"
    )


def parse_class_quotes_payload(
    payload: dict[str, Any],
    *,
    concept_name: str,
    source_url: str,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Normalize one Yahoo API page and reject malformed stock identifiers."""

    data = payload.get("data")
    if not isinstance(data, dict):
        raise ValueError(f"Yahoo class quote payload missing data: {concept_name}")
    raw_rows = data.get("list") or []
    pagination = data.get("pagination") or {}
    if not isinstance(raw_rows, list) or not isinstance(pagination, dict):
        raise ValueError(f"Yahoo class quote payload malformed: {concept_name}")

    rows: list[dict[str, Any]] = []
    for raw in raw_rows:
        if not isinstance(raw, dict):
            continue
        yahoo_symbol = str(raw.get("symbol") or "").strip()
        symbol_match = _YAHOO_SYMBOL_RE.fullmatch(yahoo_symbol)
        if symbol_match is None:
            continue
        trade_date = _date_from_yahoo_row(raw)
        rows.append(
            {
                "concept_name": concept_name,
                "stock_id": symbol_match.group("stock_id"),
                "yahoo_symbol": yahoo_symbol,
                "stock_name": str(raw.get("symbolName") or "").strip(),
                "market_suffix": symbol_match.group("market"),
                "holding_type": str(raw.get("holdingType") or "").strip(),
                "trade_date": trade_date,
                "source_url": source_url,
            }
        )
    return rows, pagination


def download_yahoo_concept_snapshot(
    *,
    class_url: str = YAHOO_CLASS_URL,
    max_workers: int = 4,
    timeout_seconds: int = 30,
    retries: int = 3,
    fetch_text: Callable[[str], str] | None = None,
    fetch_json: Callable[[str], dict[str, Any]] | None = None,
) -> YahooConceptSnapshot:
    """Download every Yahoo concept and verify all paginated member counts."""

    text_loader = fetch_text or (
        lambda url: _fetch_text(url, timeout_seconds=timeout_seconds, retries=retries)
    )
    json_loader = fetch_json or (
        lambda url: _fetch_json(url, timeout_seconds=timeout_seconds, retries=retries)
    )
    class_html = text_loader(class_url)
    categories = parse_concept_categories(class_html, base_url=class_url)
    if not categories:
        raise ValueError("Yahoo class page returned no concept categories")

    category_results: list[dict[str, Any]] = []
    membership_rows: list[dict[str, Any]] = []
    with ThreadPoolExecutor(max_workers=max(1, int(max_workers))) as executor:
        futures = {
            executor.submit(_download_category, category, json_loader): category
            for category in categories
        }
        for future in as_completed(futures):
            category_record, rows = future.result()
            category_results.append(category_record)
            membership_rows.extend(rows)

    category_frame = pd.DataFrame(category_results).sort_values("concept_name").reset_index(drop=True)
    membership_frame = (
        pd.DataFrame(membership_rows)
        .drop_duplicates(["concept_name", "stock_id"])
        .sort_values(["concept_name", "stock_id"])
        .reset_index(drop=True)
    )
    if category_frame.empty or membership_frame.empty:
        raise ValueError("Yahoo concept snapshot is empty")
    if not category_frame["reported_count"].eq(category_frame["downloaded_count"]).all():
        failed = category_frame.loc[
            ~category_frame["reported_count"].eq(category_frame["downloaded_count"]),
            ["concept_name", "reported_count", "downloaded_count"],
        ]
        raise ValueError(f"Yahoo concept pagination count mismatch: {failed.to_dict('records')}")

    available_dates = membership_frame["trade_date"].dropna().astype(str)
    if available_dates.empty:
        raise ValueError("Yahoo concept snapshot has no source trade date")
    snapshot_date = max(available_dates)
    fetched_at = datetime.now(ZoneInfo("Asia/Taipei")).isoformat(timespec="seconds")
    content_sha256 = _membership_digest(membership_frame)
    snapshot_id = f"yahoo_concept_{snapshot_date}_{content_sha256[:12]}"
    manifest = {
        "snapshot_id": snapshot_id,
        "snapshot_date": snapshot_date,
        "fetched_at": fetched_at,
        "source_url": class_url,
        "category_label": YAHOO_CATEGORY_LABEL,
        "category_count": int(category_frame["concept_name"].nunique()),
        "membership_count": int(len(membership_frame)),
        "unique_stock_count": int(membership_frame["stock_id"].nunique()),
        "content_sha256": content_sha256,
        "importance": IMPORTANT_BASELINE,
        "is_important": True,
        "membership_mode": POINT_IN_TIME_SNAPSHOT,
        "static_backfill_authorized": True,
        "status": "complete",
    }
    category_frame.insert(0, "snapshot_id", snapshot_id)
    membership_frame.insert(0, "snapshot_id", snapshot_id)
    return YahooConceptSnapshot(manifest, category_frame, membership_frame)


def write_yahoo_concept_snapshot(snapshot: YahooConceptSnapshot, *, sqlite_path: Path) -> bool:
    """Persist a complete append-only snapshot; return False when already present."""

    sqlite_path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(sqlite_path) as connection:
        _create_tables(connection)
        existing = connection.execute(
            "select content_sha256 from yahoo_concept_snapshots where snapshot_id = ?",
            [snapshot.manifest["snapshot_id"]],
        ).fetchone()
        if existing is not None:
            if str(existing[0]) != str(snapshot.manifest["content_sha256"]):
                raise ValueError("snapshot id collision with different content")
            return False
        with connection:
            connection.execute(
                """
                insert into yahoo_concept_snapshots (
                    snapshot_id, snapshot_date, fetched_at, source_url, category_label,
                    category_count, membership_count, unique_stock_count, content_sha256,
                    importance, is_important, membership_mode,
                    static_backfill_authorized, status
                ) values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    snapshot.manifest["snapshot_id"],
                    snapshot.manifest["snapshot_date"],
                    snapshot.manifest["fetched_at"],
                    snapshot.manifest["source_url"],
                    snapshot.manifest["category_label"],
                    snapshot.manifest["category_count"],
                    snapshot.manifest["membership_count"],
                    snapshot.manifest["unique_stock_count"],
                    snapshot.manifest["content_sha256"],
                    snapshot.manifest["importance"],
                    int(bool(snapshot.manifest["is_important"])),
                    snapshot.manifest["membership_mode"],
                    int(bool(snapshot.manifest["static_backfill_authorized"])),
                    snapshot.manifest["status"],
                ],
            )
            snapshot.categories.to_sql(
                "yahoo_concept_categories_stage", connection, if_exists="replace", index=False
            )
            connection.execute(
                """
                insert into yahoo_concept_categories
                select snapshot_id, concept_name, source_url, reported_count,
                       downloaded_count, max_trade_date
                from yahoo_concept_categories_stage
                """
            )
            connection.execute("drop table yahoo_concept_categories_stage")
            snapshot.membership.to_sql(
                "yahoo_concept_membership_stage", connection, if_exists="replace", index=False
            )
            connection.execute(
                """
                insert into yahoo_concept_membership
                select snapshot_id, concept_name, stock_id, yahoo_symbol, stock_name,
                       market_suffix, holding_type, trade_date, source_url
                from yahoo_concept_membership_stage
                """
            )
            connection.execute("drop table yahoo_concept_membership_stage")
    return True


def load_important_yahoo_concept_snapshot(
    sqlite_path: Path,
    *,
    snapshot_id: str | None = None,
) -> tuple[dict[str, Any], pd.DataFrame]:
    """Load an explicit snapshot or the latest complete important snapshot."""

    with sqlite3.connect(sqlite_path) as connection:
        _create_tables(connection)
        if snapshot_id:
            row = connection.execute(
                "select * from yahoo_concept_snapshots where snapshot_id = ? and status = 'complete'",
                [snapshot_id],
            ).fetchone()
        else:
            row = connection.execute(
                """
                select * from yahoo_concept_snapshots
                where is_important = 1 and status = 'complete'
                order by snapshot_date desc, fetched_at desc, snapshot_id desc
                limit 1
                """
            ).fetchone()
        if row is None:
            raise ValueError(f"No complete important Yahoo concept snapshot in {sqlite_path}")
        columns = [item[1] for item in connection.execute("pragma table_info(yahoo_concept_snapshots)")]
        manifest = dict(zip(columns, row, strict=True))
        membership = pd.read_sql_query(
            """
            select * from yahoo_concept_membership
            where snapshot_id = ?
            order by concept_name, stock_id
            """,
            connection,
            params=[manifest["snapshot_id"]],
            dtype={"stock_id": str},
        )
    return manifest, membership


def write_snapshot_exports(snapshot: YahooConceptSnapshot, *, output_dir: Path) -> None:
    """Write an auditable local CSV/JSON sidecar for the SQLite snapshot."""

    output_dir.mkdir(parents=True, exist_ok=True)
    snapshot.categories.to_csv(
        output_dir / "yahoo_concept_categories.csv",
        index=False,
        encoding="utf-8-sig",
        lineterminator="\n",
    )
    snapshot.membership.to_csv(
        output_dir / "yahoo_concept_membership.csv",
        index=False,
        encoding="utf-8-sig",
        lineterminator="\n",
    )
    (output_dir / "yahoo_concept_snapshot_manifest.json").write_text(
        json.dumps(snapshot.manifest, ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8",
        newline="\n",
    )


def membership_mode_for_date(
    asof_date: str,
    *,
    snapshot_date: str,
    allow_static_current_backfill: bool,
) -> str:
    if str(asof_date) < str(snapshot_date):
        if not allow_static_current_backfill:
            return "point_in_time_unavailable"
        return STATIC_CURRENT_BACKFILL
    return POINT_IN_TIME_SNAPSHOT


def _download_category(
    category: YahooConceptCategory,
    json_loader: Callable[[str], dict[str, Any]],
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    rows: list[dict[str, Any]] = []
    seen_offsets: set[int] = set()
    offset = 0
    results_total: int | None = None
    while True:
        if offset in seen_offsets:
            raise ValueError(f"Yahoo pagination loop: {category.concept_name} offset={offset}")
        seen_offsets.add(offset)
        payload = json_loader(build_class_quotes_api_url(category.concept_name, offset=offset))
        page_rows, pagination = parse_class_quotes_payload(
            payload,
            concept_name=category.concept_name,
            source_url=category.source_url,
        )
        rows.extend(page_rows)
        current_total = int(pagination.get("resultsTotal") or 0)
        if results_total is None:
            results_total = current_total
        elif current_total != results_total:
            raise ValueError(f"Yahoo result total changed during download: {category.concept_name}")
        next_offset = pagination.get("nextOffset")
        if next_offset in (None, ""):
            break
        offset = int(next_offset)
        if offset >= int(results_total or 0):
            break

    deduped = {row["stock_id"]: row for row in rows}
    normalized_rows = sorted(deduped.values(), key=lambda row: row["stock_id"])
    reported_count = int(results_total or 0)
    max_trade_date = max((str(row["trade_date"]) for row in normalized_rows if row["trade_date"]), default="")
    record = {
        "concept_name": category.concept_name,
        "source_url": category.source_url,
        "reported_count": reported_count,
        "downloaded_count": len(normalized_rows),
        "max_trade_date": max_trade_date,
    }
    return record, normalized_rows


def _date_from_yahoo_row(row: dict[str, Any]) -> str:
    for key in ("tradeDate", "regularMarketTime"):
        value = str(row.get(key) or "").strip()
        if value:
            return value[:10]
    return ""


def _membership_digest(frame: pd.DataFrame) -> str:
    fields = ["concept_name", "stock_id", "yahoo_symbol", "stock_name", "market_suffix"]
    payload = "\n".join(
        "|".join(str(row[field]) for field in fields)
        for row in frame.sort_values(["concept_name", "stock_id"])[fields].to_dict("records")
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _fetch_text(url: str, *, timeout_seconds: int, retries: int) -> str:
    return _fetch_bytes(url, timeout_seconds=timeout_seconds, retries=retries).decode(
        "utf-8", "replace"
    )


def _fetch_json(url: str, *, timeout_seconds: int, retries: int) -> dict[str, Any]:
    payload = json.loads(
        _fetch_bytes(url, timeout_seconds=timeout_seconds, retries=retries).decode(
            "utf-8", "replace"
        )
    )
    if not isinstance(payload, dict):
        raise ValueError(f"Yahoo resource returned non-object JSON: {url}")
    return payload


def _fetch_bytes(url: str, *, timeout_seconds: int, retries: int) -> bytes:
    request = Request(
        url,
        headers={
            "Accept": "application/json,text/html;q=0.9,*/*;q=0.8",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) ABC-Quant-Research/1.0",
        },
    )
    last_error: Exception | None = None
    for attempt in range(max(1, int(retries))):
        try:
            with urlopen(request, timeout=timeout_seconds) as response:
                return response.read()
        except Exception as exc:  # pragma: no cover - network failures vary by host
            last_error = exc
            if attempt + 1 < retries:
                time.sleep(0.5 * (2**attempt))
    raise RuntimeError(f"Yahoo request failed after {retries} attempts: {url}") from last_error


def _create_tables(connection: sqlite3.Connection) -> None:
    connection.executescript(
        """
        create table if not exists yahoo_concept_snapshots (
            snapshot_id text primary key,
            snapshot_date text not null,
            fetched_at text not null,
            source_url text not null,
            category_label text not null,
            category_count integer not null,
            membership_count integer not null,
            unique_stock_count integer not null,
            content_sha256 text not null,
            importance text not null,
            is_important integer not null,
            membership_mode text not null,
            static_backfill_authorized integer not null,
            status text not null
        );
        create table if not exists yahoo_concept_categories (
            snapshot_id text not null,
            concept_name text not null,
            source_url text not null,
            reported_count integer not null,
            downloaded_count integer not null,
            max_trade_date text,
            primary key (snapshot_id, concept_name),
            foreign key (snapshot_id) references yahoo_concept_snapshots(snapshot_id)
        );
        create table if not exists yahoo_concept_membership (
            snapshot_id text not null,
            concept_name text not null,
            stock_id text not null,
            yahoo_symbol text not null,
            stock_name text,
            market_suffix text not null,
            holding_type text,
            trade_date text,
            source_url text not null,
            primary key (snapshot_id, concept_name, stock_id),
            foreign key (snapshot_id) references yahoo_concept_snapshots(snapshot_id)
        );
        create index if not exists idx_yahoo_concept_membership_stock
            on yahoo_concept_membership(snapshot_id, stock_id);
        """
    )
