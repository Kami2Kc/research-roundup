"""Command-line entry point: `roundup <command>`."""

import logging
from collections import Counter
from contextlib import closing
from datetime import date, timedelta

import typer

from roundup import db, editor, export as exporter, newsletter
from roundup.collectors import collect_all
from roundup.health import source_health
from roundup.collectors.base import HttpClient
from roundup.config import REPO_ROOT, load_settings, load_sources
from roundup.llm import LLMError, estimate_cost, get_llm
from roundup.models import Source
from roundup.screening import PROMPT_VERSION as SCREEN_PROMPT_VERSION, screen_papers

app = typer.Typer(help="The Research Roundup pipeline.", no_args_is_help=True)

DEFAULT_LOOKBACK_DAYS = 14  # weekly runs overlap by a week; upserts make the overlap harmless


@app.callback()
def main(verbose: bool = typer.Option(False, "--verbose", "-v", help="Show debug logging.")) -> None:
    logging.basicConfig(level=logging.DEBUG if verbose else logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    for name in ("httpx", "httpx2"):  # the anthropic SDK logs every request through httpx2
        logging.getLogger(name).setLevel(logging.WARNING)


def fail(message: str) -> None:
    typer.echo(f"Error: {message}", err=True)
    raise typer.Exit(code=1)


def not_implemented(milestone: str) -> None:
    fail(f"not implemented yet (planned for {milestone}).")


def enabled_sources() -> list[Source]:
    return [s for s in load_sources() if s.enabled]


@app.command()
def collect(
    since: str | None = typer.Option(None, help="Only keep items published on or after this date (YYYY-MM-DD). "
                                                f"Default: {DEFAULT_LOOKBACK_DAYS} days ago."),
    source: str | None = typer.Option(None, help="Only collect from this source ID."),
) -> None:
    """Fetch new publications."""
    settings = load_settings()
    if not settings.contact_email:
        fail("CONTACT_EMAIL is not set (see .env.example); it is required for a polite User-Agent.")
    since_date = date.fromisoformat(since) if since else date.today() - timedelta(days=DEFAULT_LOOKBACK_DAYS)
    sources = enabled_sources()
    if source:
        sources = [s for s in sources if s.id == source]
        if not sources:
            fail(f"no enabled source with ID '{source}'.")

    with closing(db.connect()) as conn:
        results = collect_all(conn, sources, HttpClient(settings.contact_email), since_date)

    typer.echo(f"\n{'SOURCE':<18} {'STATUS':<7} {'FOUND':>6} {'NEW':>5}  ERROR")
    for r in results:
        typer.echo(f"{r.source_id:<18} {r.status:<7} {r.found:>6} {r.new:>5}  {r.error or ''}")
    failed = sum(r.status == "error" for r in results)
    typer.echo(f"\n{len(results)} sources, {sum(r.new for r in results)} new papers, {failed} failed.")


@app.command()
def screen(
    limit: int | None = typer.Option(None, help="Maximum LLM calls this run (default: SCREEN_LIMIT)."),
    since: str | None = typer.Option(None, help="Only screen papers published on or after this date (YYYY-MM-DD)."),
) -> None:
    """Classify papers that haven't been screened yet."""
    settings = load_settings()
    if not settings.llm_screen_model:
        fail("LLM_SCREEN_MODEL is not set (see .env.example).")
    try:
        llm = get_llm(settings)
    except LLMError as e:
        fail(str(e))
    sources = {s.id: s for s in load_sources()}
    with closing(db.connect()) as conn:
        stats = screen_papers(conn, llm, settings.llm_screen_model, sources, limit or settings.screen_limit,
                              since=date.fromisoformat(since) if since else None)
    typer.echo(
        f"Screened {stats.screened}, skipped {stats.no_abstract} without an abstract, {stats.errors} errors. "
        f"Tokens: {stats.input_tokens:,} in / {stats.output_tokens:,} out, estimated cost ${stats.cost_usd:.4f}."
    )


@app.command("build-issue")
def build_issue(
    month: str = typer.Option(..., help="Issue month (YYYY-MM)."),
    render_only: bool = typer.Option(False, help="Re-render the stored issue without calling the editor."),
) -> None:
    """Build the newsletter for a month."""
    settings = load_settings()
    all_sources = load_sources()
    sources = {s.id: s for s in all_sources}
    with closing(db.connect()) as conn:
        try:
            if render_only:
                issue = newsletter.load_issue(conn, month, sources)
            else:
                if not settings.llm_editor_model:
                    fail("LLM_EDITOR_MODEL is not set (see .env.example).")
                issue = editor.build_issue(conn, get_llm(settings), settings.llm_editor_model, month, sources,
                                           settings.relevance_threshold)
        except (LLMError, ValueError) as e:
            fail(str(e))
        path = newsletter.write(conn, issue, sources_monitored=sum(s.enabled for s in all_sources),
                                site_url=settings.site_url)
        usage = conn.execute("SELECT model, input_tokens, output_tokens FROM issues WHERE month = ?", (month,)).fetchone()
    typer.echo(f"{month}: {len(issue.papers)} papers chosen from a pool of {issue.pool_size}. Wrote {path}")
    if not render_only:
        cost = estimate_cost(usage["model"], usage["input_tokens"], usage["output_tokens"])
        typer.echo(f"Editor tokens: {usage['input_tokens']:,} in / {usage['output_tokens']:,} out, "
                   f"estimated cost ${cost or 0:.4f}.")


@app.command()
def export() -> None:
    """Write the JSON files for the dashboard."""
    with closing(db.connect()) as conn:
        counts = exporter.export_all(conn, load_sources())
    typer.echo(f"Exported {counts['issues']} issues, {counts['papers']} papers and {counts['sources']} sources.")


@app.command("run-weekly")
def run_weekly() -> None:
    """Collect, screen, then export."""
    not_implemented("M5")


@app.command("run-monthly")
def run_monthly() -> None:
    """Collect, screen, build the previous month's issue, then export."""
    not_implemented("M5")


@app.command()
def backfill(
    from_: str = typer.Option(..., "--from", help="Start date (YYYY-MM-DD)."),
    to: str = typer.Option(..., help="End date (YYYY-MM-DD)."),
) -> None:
    """Collect, screen and build issues for past months."""
    not_implemented("M5")


@app.command("sources-report")
def sources_report(
    markdown: bool = typer.Option(False, help="Print a Markdown table (for docs/SOURCES.md)."),
) -> None:
    """Print the coverage and health table."""
    with closing(db.connect()) as conn:
        report = source_health(conn, load_sources())

    def abstracts(h) -> str:
        return f"{h.with_abstract}/{h.papers}" if h.papers else "–"

    if markdown:
        typer.echo("| Source | Group | Method | Status | Papers with abstracts | Last run |")
        typer.echo("|---|---|---|---|---|---|")
        for h in report:
            last = h.last_run["started_at"][:10] if h.last_run else "–"
            typer.echo(f"| {h.source.name} | {h.source.group} | {h.source.method} | {h.status} | {abstracts(h)} | {last} |")
    else:
        typer.echo(f"{'ID':<16} {'GROUP':<13} {'METHOD':<9} {'STATUS':<12} {'ABSTRACTS':>9}  {'LAST RUN':<17} ERROR")
        for h in report:
            run = h.last_run
            last = f"{run['started_at'][:16]}" if run else "–"
            typer.echo(f"{h.source.id:<16} {h.source.group:<13} {h.source.method:<9} {h.status:<12} "
                       f"{abstracts(h):>9}  {last:<17} {(run or {}).get('error') or ''}")

    statuses = Counter(h.status for h in report)
    typer.echo(f"\n{len(report)} sources: " + ", ".join(f"{n} {status}" for status, n in statuses.most_common()))


@app.command("eval")
def eval_() -> None:
    """Compare the model's market focus with eval/labels.csv."""
    from roundup.eval import LABELS, run_eval

    settings = load_settings()
    if not settings.llm_screen_model:
        fail("LLM_SCREEN_MODEL is not set (see .env.example).")
    labels_path = REPO_ROOT / "eval" / "labels.csv"
    try:
        report = run_eval(get_llm(settings), settings.llm_screen_model, labels_path,
                          REPO_ROOT / "eval" / "results.csv")
    except (LLMError, ValueError) as e:
        fail(str(e))
    if not report.rows:
        fail(f"no labelled rows in {labels_path} (fill in label_market_focus).")

    n = len(report.rows)
    typer.echo(f"Market focus: model agrees with the label on {round(report.agreement * n)}/{n} papers "
               f"({report.agreement:.0%}); Cohen's kappa {report.kappa:.2f}. Prompt {SCREEN_PROMPT_VERSION}.")
    confusion = report.confusion()
    typer.echo(f"\n{'label \\ model':<14}" + "".join(f"{c:>13}" for c in LABELS))
    for label in LABELS:
        typer.echo(f"{label:<14}" + "".join(f"{confusion.get((label, c), 0):>13}" for c in LABELS))
    if (mae := report.relevance_mae()) is not None:
        typer.echo(f"\nRelevance: mean absolute difference from your scores {mae:.1f} points.")
    disagreements = [r for r in report.rows if r["label"] != r["predicted"]]
    if disagreements:
        typer.echo("\nDisagreements:")
        for r in disagreements:
            typer.echo(f"- {r['title'][:70]}: label {r['label']}, model {r['predicted']}. {r['rationale']}")
    typer.echo(f"\nDetails in eval/results.csv. Estimated cost ${report.cost_usd:.4f}.")


if __name__ == "__main__":
    app()
