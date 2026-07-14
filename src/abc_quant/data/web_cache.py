"""Persistent web-source cache for the walkline scanner."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import json
from pathlib import Path
import sqlite3
from typing import Any


@dataclass(frozen=True)
class WebCachePaths:
    cache_dir: Path
    sqlite_path: Path
    jsonl_path: Path


def build_web_cache_paths(cache_dir: str | Path) -> WebCachePaths:
    root = Path(cache_dir)
    return WebCachePaths(
        cache_dir=root,
        sqlite_path=root / "web_search_cache.sqlite",
        jsonl_path=root / "web_sources.jsonl",
    )


class WebSourceCache:
    """Small SQLite + JSONL cache for supplemental web/event records."""

    def __init__(self, cache_dir: str | Path) -> None:
        self.paths = build_web_cache_paths(cache_dir)
        self.paths.cache_dir.mkdir(parents=True, exist_ok=True)
        self._init_sqlite()

    def append_records(self, records: list[dict[str, Any]]) -> None:
        if not records:
            return
        with sqlite3.connect(self.paths.sqlite_path) as connection:
            connection.executemany(
                """
                insert into web_sources (
                    fetched_at, asof_date, stock_id, stock_name, source_name, url,
                    title, published_at, source_priority, content_summary,
                    used_in_score, used_in_report, confidence, published_at_unknown,
                    raw_json
                ) values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                [self._record_to_row(record) for record in records],
            )
        write_web_sources_jsonl(self.paths.jsonl_path, records, append=True)

    def read_records(self, *, asof_date: str, stock_id: str | None = None) -> list[dict[str, Any]]:
        query = "select raw_json from web_sources where asof_date = ?"
        params: list[Any] = [asof_date]
        if stock_id:
            query += " and stock_id = ?"
            params.append(stock_id)
        with sqlite3.connect(self.paths.sqlite_path) as connection:
            rows = connection.execute(query, params).fetchall()
        return [json.loads(row[0]) for row in rows]

    def _init_sqlite(self) -> None:
        with sqlite3.connect(self.paths.sqlite_path) as connection:
            connection.execute(
                """
                create table if not exists web_sources (
                    id integer primary key autoincrement,
                    fetched_at text not null,
                    asof_date text not null,
                    stock_id text not null,
                    stock_name text,
                    source_name text,
                    url text,
                    title text,
                    published_at text,
                    source_priority text,
                    content_summary text,
                    used_in_score integer,
                    used_in_report integer,
                    confidence text,
                    published_at_unknown integer,
                    raw_json text not null
                )
                """
            )

    @staticmethod
    def _record_to_row(record: dict[str, Any]) -> tuple[Any, ...]:
        normalized = normalize_web_record(record)
        return (
            normalized["fetched_at"],
            normalized["asof_date"],
            normalized["stock_id"],
            normalized.get("stock_name", ""),
            normalized.get("source_name", ""),
            normalized.get("url", ""),
            normalized.get("title", ""),
            normalized.get("published_at", ""),
            normalized.get("source_priority", ""),
            normalized.get("content_summary", ""),
            int(bool(normalized.get("used_in_score", False))),
            int(bool(normalized.get("used_in_report", True))),
            normalized.get("confidence", "low"),
            int(bool(normalized.get("published_at_unknown", False))),
            json.dumps(normalized, ensure_ascii=False, sort_keys=True),
        )


def normalize_web_record(record: dict[str, Any]) -> dict[str, Any]:
    normalized = dict(record)
    normalized.setdefault("fetched_at", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    normalized.setdefault("asof_date", "")
    normalized.setdefault("stock_id", "")
    normalized.setdefault("stock_name", "")
    normalized.setdefault("source_name", "")
    normalized.setdefault("url", "")
    normalized.setdefault("title", "")
    normalized.setdefault("published_at", "")
    normalized.setdefault("source_priority", "community")
    normalized.setdefault("content_summary", "")
    normalized.setdefault("used_in_score", False)
    normalized.setdefault("used_in_report", True)
    normalized.setdefault("confidence", "low")
    normalized.setdefault("published_at_unknown", not bool(normalized.get("published_at")))
    return normalized


def write_web_sources_jsonl(
    path: str | Path,
    records: list[dict[str, Any]],
    *,
    append: bool = False,
) -> None:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    mode = "a" if append else "w"
    with output_path.open(mode, encoding="utf-8") as fh:
        for record in records:
            fh.write(json.dumps(normalize_web_record(record), ensure_ascii=False, sort_keys=True))
            fh.write("\n")
