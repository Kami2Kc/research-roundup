"""Command-line entry point: `roundup <command>`."""

from collections import Counter

import typer

from roundup.config import load_sources

app = typer.Typer(help="The Research Roundup pipeline.", no_args_is_help=True)


def not_implemented(milestone: str) -> None:
    typer.echo(f"Not implemented yet (planned for {milestone}).", err=True)
    raise typer.Exit(code=1)


@app.command()
def collect(
    since: str | None = typer.Option(None, help="Only fetch items published on or after this date (YYYY-MM-DD)."),
    source: str | None = typer.Option(None, help="Only collect from this source ID."),
) -> None:
    """Fetch new publications."""
    not_implemented("M1")


@app.command()
def screen(limit: int | None = typer.Option(None, help="Maximum number of papers to screen in this run.")) -> None:
    """Classify papers that haven't been screened yet."""
    not_implemented("M1")


@app.command("build-issue")
def build_issue(month: str = typer.Option(..., help="Issue month (YYYY-MM).")) -> None:
    """Build the newsletter for a month."""
    not_implemented("M1")


@app.command()
def export() -> None:
    """Write the JSON files for the dashboard."""
    not_implemented("M1")


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
def sources_report() -> None:
    """Print the coverage and health table."""
    sources = load_sources()
    typer.echo(f"{'ID':<22} {'GROUP':<14} {'METHOD':<9} {'ENABLED':<8} NAME")
    for s in sources:
        typer.echo(f"{s.id:<22} {s.group:<14} {s.method:<9} {'yes' if s.enabled else 'no':<8} {s.name}")

    enabled = sum(s.enabled for s in sources)
    by_method = Counter(str(s.method) for s in sources)
    typer.echo(f"\n{len(sources)} sources, {enabled} enabled. By method: {dict(sorted(by_method.items()))}")


@app.command("eval")
def eval_() -> None:
    """Compare the model's market focus with eval/labels.csv."""
    not_implemented("M3")


if __name__ == "__main__":
    app()
