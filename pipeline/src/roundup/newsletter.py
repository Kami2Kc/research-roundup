"""Render an issue as email-safe HTML: table layout, 600px wide, inlined CSS, no JavaScript."""

import json
import sqlite3
from datetime import date, datetime
from pathlib import Path

import css_inline
from jinja2 import Environment, FileSystemLoader, select_autoescape

from roundup.config import WEB_PUBLIC
from roundup.editor import SOURCE_TYPES, BuiltIssue
from roundup.models import Source

TEMPLATES = Path(__file__).resolve().parents[2] / "templates"

# The same colours are used by the dashboard (web/src/lib/tags.ts): each tag always looks the same.
TAG_COLOURS = {
    "EM": {"bg": "#fef3c7", "fg": "#92400e"},
    "DM": {"bg": "#dbeafe", "fg": "#1e40af"},
    "Transversal": {"bg": "#ede9fe", "fg": "#5b21b6"},
}

_env = Environment(loader=FileSystemLoader(TEMPLATES), autoescape=select_autoescape(["html", "j2"]))
# Keep @media rules in a <style> tag so the layout still adapts on phones after inlining.
_inliner = css_inline.CSSInliner(keep_at_rules=True, load_remote_stylesheets=False)


def render(issue: BuiltIssue, issue_number: int, sources_monitored: int, site_url: str | None = None,
           sources_tracked: int | None = None) -> str:
    papers = []
    for p in issue.papers:
        authors = p["authors"]
        published = date.fromisoformat(p["published_date"])
        papers.append({
            **p,
            "published_label": f"{published.day} {published:%b %Y}",
            "authors_label": ", ".join(authors[:4]) + (" et al." if len(authors) > 4 else ""),
            "source_type": SOURCE_TYPES.get(p["source_group"], ""),
        })
    note_paragraphs = [para.strip() for para in issue.editor_note.split("\n\n") if para.strip()]
    html = _env.get_template("newsletter.html.j2").render(
        month=issue.month,
        month_label=datetime.strptime(issue.month, "%Y-%m").strftime("%B %Y"),
        issue_number=issue_number,
        preheader=note_paragraphs[0][:150] if note_paragraphs else "",
        note_paragraphs=note_paragraphs,
        papers=papers,
        tag_colours=TAG_COLOURS,
        sources_monitored=sources_monitored,
        sources_tracked=sources_tracked,
        papers_screened=issue.papers_screened,
        pool_size=issue.pool_size,
        site_url=(site_url or "").rstrip("/"),
    )
    return _inliner.inline(html)


def write(conn: sqlite3.Connection, issue: BuiltIssue, sources_monitored: int, site_url: str | None = None,
          out_dir: Path = WEB_PUBLIC / "newsletters", sources_tracked: int | None = None) -> Path:
    issue_number = conn.execute("SELECT COUNT(*) FROM issues WHERE month <= ?", (issue.month,)).fetchone()[0]
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"{issue.month}.html"
    path.write_text(render(issue, issue_number, sources_monitored, site_url, sources_tracked), encoding="utf-8")
    return path


def load_issue(conn: sqlite3.Connection, month: str, sources: dict[str, Source]) -> BuiltIssue:
    """Rebuild a stored issue from the database (to re-render without calling the editor again)."""
    row = conn.execute("SELECT * FROM issues WHERE month = ?", (month,)).fetchone()
    if row is None:
        raise ValueError(f"No issue stored for {month}")
    papers = []
    for ip in conn.execute(
        """SELECT ip.*, p.title, p.authors, p.url, p.published_date, p.paywalled, p.source_id,
                  s.market_focus AS screening_focus
           FROM issue_papers ip JOIN papers p ON p.id = ip.paper_id JOIN screenings s ON s.paper_id = p.id
           WHERE ip.month = ? ORDER BY ip.position""",
        (month,),
    ):
        source = sources[ip["source_id"]]
        papers.append({**dict(ip), "id": ip["paper_id"], "authors": json.loads(ip["authors"]),
                       "takeaways": json.loads(ip["takeaways"]), "source_name": source.name,
                       "source_group": str(source.group)})
    return BuiltIssue(month, row["editor_note"], row["selection_rationale"], papers, row["pool_size"],
                      row["papers_screened"])
