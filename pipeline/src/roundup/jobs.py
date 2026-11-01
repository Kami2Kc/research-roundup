"""The scheduled jobs the CLI and GitHub Actions run: weekly, monthly and backfill.

Each job is a short sequence of the pipeline's steps, so it can be moved to any scheduler unchanged.
"""

import logging
import sqlite3
from dataclasses import dataclass, field
from datetime import date, timedelta
from pathlib import Path

from roundup import editor, export, newsletter
from roundup.collectors import RunResult, collect_all
from roundup.collectors.base import HttpClient
from roundup.config import WEB_PUBLIC, Settings
from roundup.llm import LLM
from roundup.models import Source
from roundup.screening import ScreeningStats, screen_papers

log = logging.getLogger(__name__)

WEEKLY_LOOKBACK_DAYS = 14  # runs overlap by a week; upserts make the overlap harmless


@dataclass
class Context:
    conn: sqlite3.Connection
    settings: Settings
    sources: list[Source]  # every configured source (collection uses the enabled ones)
    http: HttpClient
    llm: LLM | None  # None for steps that make no LLM calls
    web_public: Path = WEB_PUBLIC  # where newsletters and JSON for the dashboard are written

    @property
    def enabled(self) -> list[Source]:
        return [s for s in self.sources if s.enabled]

    @property
    def by_id(self) -> dict[str, Source]:
        return {s.id: s for s in self.sources}


@dataclass
class JobReport:
    collected: list[RunResult] = field(default_factory=list)
    screened: ScreeningStats | None = None
    issues: list[editor.BuiltIssue] = field(default_factory=list)

    @property
    def all_sources_failed(self) -> bool:
        return bool(self.collected) and all(r.status == "error" for r in self.collected)


def previous_month(today: date) -> str:
    return (today.replace(day=1) - timedelta(days=1)).strftime("%Y-%m")


def months_between(start: date, end: date) -> list[str]:
    """Every month from start's month to end's month, inclusive, as YYYY-MM."""
    months, current = [], start.replace(day=1)
    while current <= end:
        months.append(current.strftime("%Y-%m"))
        current = (current + timedelta(days=32)).replace(day=1)
    return months


def build_and_render(ctx: Context, month: str) -> editor.BuiltIssue:
    """Run the editor for a month and write its newsletter HTML."""
    issue = editor.build_issue(ctx.conn, ctx.llm, ctx.settings.llm_editor_model, month, ctx.by_id,
                               ctx.settings.relevance_threshold)
    newsletter.write(ctx.conn, issue, sources_monitored=len(ctx.enabled), site_url=ctx.settings.site_url,
                     sources_tracked=len(ctx.sources),
                     out_dir=ctx.web_public / "newsletters")
    return issue


def run_weekly(ctx: Context, today: date) -> JobReport:
    report = JobReport()
    report.collected = collect_all(ctx.conn, ctx.enabled, ctx.http, today - timedelta(days=WEEKLY_LOOKBACK_DAYS))
    report.screened = screen_papers(ctx.conn, ctx.llm, ctx.settings.llm_screen_model, ctx.by_id,
                                    ctx.settings.screen_limit)
    export.export_all(ctx.conn, ctx.sources, out_dir=ctx.web_public / "data")
    return report


def run_monthly(ctx: Context, month: str) -> JobReport:
    """Collect from the start of the month first, so papers from its last days are in the pool."""
    report = JobReport()
    report.collected = collect_all(ctx.conn, ctx.enabled, ctx.http, date.fromisoformat(f"{month}-01"))
    report.screened = screen_papers(ctx.conn, ctx.llm, ctx.settings.llm_screen_model, ctx.by_id,
                                    ctx.settings.screen_limit)
    report.issues.append(build_and_render(ctx, month))
    export.export_all(ctx.conn, ctx.sources, out_dir=ctx.web_public / "data")
    return report


def backfill(ctx: Context, start: date, end: date, limit: int, rebuild: bool = False) -> JobReport:
    """Collect and screen a past period, then build an issue for each month in it (skipping built ones)."""
    report = JobReport()
    report.collected = collect_all(ctx.conn, ctx.enabled, ctx.http, start)
    report.screened = screen_papers(ctx.conn, ctx.llm, ctx.settings.llm_screen_model, ctx.by_id, limit,
                                    since=start, until=end)
    built = {row[0] for row in ctx.conn.execute("SELECT month FROM issues")}
    for month in months_between(start, end):
        if month in built and not rebuild:
            continue
        try:
            report.issues.append(build_and_render(ctx, month))
        except editor.EmptyPoolError as e:
            log.warning("Skipping %s: %s", month, e)
    export.export_all(ctx.conn, ctx.sources, out_dir=ctx.web_public / "data")
    return report
