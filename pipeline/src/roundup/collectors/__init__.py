"""Run the collector for each source and store the results. One source failing never stops the run."""

import logging
import re
import sqlite3
import time
from dataclasses import dataclass
from datetime import date

from roundup import db
from roundup.collectors import crossref, openalex, rss
from roundup.collectors.base import HttpClient
from roundup.models import Method, Paper, Source

log = logging.getLogger(__name__)

COLLECTORS = {
    Method.CROSSREF: crossref.collect,
    Method.RSS: rss.collect,
}


@dataclass
class RunResult:
    source_id: str
    status: str
    found: int
    new: int
    error: str | None
    duration_s: float


def collect_all(conn: sqlite3.Connection, sources: list[Source], http: HttpClient, since: date) -> list[RunResult]:
    return [collect_source(conn, source, http, since) for source in sources]


def collect_source(conn: sqlite3.Connection, source: Source, http: HttpClient, since: date) -> RunResult:
    started_at, t0 = db.now_utc(), time.monotonic()
    found = new = 0
    error = None
    try:
        collector = COLLECTORS.get(source.method)
        if collector is None:
            raise NotImplementedError(f"no collector for method '{source.method}' yet")
        papers = apply_filters(source, collector(source, http, since), since)
        found = len(papers)
        if source.fallback == Method.OPENALEX:
            openalex.fill_abstracts(papers, http)
        new = db.upsert_papers(conn, papers)
    except Exception as e:  # noqa: BLE001 - any failure is recorded against this source only
        error = f"{type(e).__name__}: {e}"
        log.warning("%s failed: %s", source.id, error)
    result = RunResult(source.id, "error" if error else "ok", found, new, error, time.monotonic() - t0)
    db.record_run(conn, source.id, started_at, result.status, found, new, error, result.duration_s)
    return result


def apply_filters(source: Source, papers: list[Paper], since: date) -> list[Paper]:
    """Apply the source's link/exclude patterns and drop items published before `since`."""
    kept = []
    for p in papers:
        if source.link_pattern and not re.search(source.link_pattern, p.url):
            continue
        if source.exclude_pattern and re.search(source.exclude_pattern, f"{p.title} {p.raw_meta.get('series') or ''}"):
            continue
        if p.published_date and p.published_date < since:
            continue
        kept.append(p)
    return kept
