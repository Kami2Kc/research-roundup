"""Write the JSON files the dashboard reads: issues.json, papers.json and sources.json."""

import json
import re
import sqlite3
from pathlib import Path

from roundup.config import WEB_PUBLIC
from roundup.health import source_health
from roundup.models import Source


def slugify(paper_id: str) -> str:
    """A URL-safe version of a paper ID (DOIs contain slashes): 10.3386/w35838 -> 10-3386-w35838."""
    return re.sub(r"[^a-z0-9]+", "-", paper_id.lower()).strip("-")


def export_all(conn: sqlite3.Connection, sources: list[Source], out_dir: Path = WEB_PUBLIC / "data") -> dict[str, int]:
    out_dir.mkdir(parents=True, exist_ok=True)
    by_id = {s.id: s for s in sources}
    issues = export_issues(conn)
    papers = export_papers(conn, by_id)
    source_rows = export_sources(conn, sources)
    for name, data in (("issues", issues), ("papers", papers), ("sources", source_rows)):
        (out_dir / f"{name}.json").write_text(json.dumps(data, indent=1, ensure_ascii=False), encoding="utf-8")
    return {"issues": len(issues), "papers": len(papers), "sources": len(source_rows)}


def export_issues(conn: sqlite3.Connection) -> list[dict]:
    issues = []
    for row in conn.execute("SELECT * FROM issues ORDER BY month DESC"):
        entries = conn.execute(
            "SELECT * FROM issue_papers WHERE month = ? ORDER BY position", (row["month"],)
        ).fetchall()
        issues.append({
            "month": row["month"],
            "editor_note": row["editor_note"],
            "selection_rationale": row["selection_rationale"],
            "newsletter": f"/newsletters/{row['month']}.html",
            "pool_size": row["pool_size"],
            "papers_screened": row["papers_screened"],
            "built_at": row["built_at"],
            "papers": [
                {
                    "slug": slugify(e["paper_id"]),
                    "position": e["position"],
                    "headline": e["headline"],
                    "selection_reason": e["selection_reason"],
                    "market_focus": e["market_focus"],
                }
                for e in entries
            ],
        })
    return issues


def export_papers(conn: sqlite3.Connection, sources: dict[str, Source]) -> list[dict]:
    """Every screened paper with its metadata, classification and the issues it appeared in."""
    membership: dict[str, list[str]] = {}
    for row in conn.execute("SELECT paper_id, month FROM issue_papers ORDER BY month"):
        membership.setdefault(row["paper_id"], []).append(row["month"])

    papers = []
    for row in conn.execute(
        """SELECT p.*, s.relevance_score, s.market_focus, s.focus_rationale, s.topics, s.regions,
                  s.model, s.prompt_version
           FROM papers p JOIN screenings s ON s.paper_id = p.id
           WHERE s.status = 'screened' ORDER BY p.published_date DESC"""
    ):
        source = sources.get(row["source_id"])
        papers.append({
            "id": row["id"],
            "slug": slugify(row["id"]),
            "title": row["title"],
            "authors": json.loads(row["authors"]),
            "abstract": row["abstract"],
            "url": row["url"],
            "published_date": row["published_date"],
            "paywalled": bool(row["paywalled"]),
            "source_id": row["source_id"],
            "source_name": source.name if source else row["source_id"],
            "source_group": str(source.group) if source else None,
            "relevance_score": row["relevance_score"],
            "market_focus": row["market_focus"],
            "focus_rationale": row["focus_rationale"],
            "topics": json.loads(row["topics"]),
            "regions": json.loads(row["regions"]),
            "model": row["model"],
            "prompt_version": row["prompt_version"],
            "issues": membership.get(row["id"], []),
        })
    return papers


def export_sources(conn: sqlite3.Connection, sources: list[Source]) -> list[dict]:
    """Every configured source, with its health status, paper counts and latest run (including sources we don't collect)."""
    rows = []
    for h in source_health(conn, sources):
        s, run = h.source, h.last_run
        rows.append({
            "id": s.id,
            "name": s.name,
            "group": str(s.group),
            "country_or_region": s.country_or_region,
            "method": str(s.method),
            "fallback": str(s.fallback) if s.fallback else None,
            "paywalled": s.paywalled,
            "enabled": s.enabled,
            "url": s.url,
            "notes": s.notes,
            "status": h.status,
            "paper_count": h.papers,
            "papers_with_abstract": h.with_abstract,
            "last_success": h.last_success,
            "last_run": {k: run[k] for k in ("started_at", "status", "items_found", "items_new", "error", "duration_s")}
            if run else None,
        })
    return rows
