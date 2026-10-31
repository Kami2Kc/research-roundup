"""Coverage and health of every source, from the config and the recorded collection runs."""

import sqlite3
from dataclasses import dataclass

from roundup.models import Source
from roundup.screening import MIN_ABSTRACT_CHARS

PARTIAL_BELOW = 0.5  # a source whose papers mostly lack abstracts is only partly covered


@dataclass
class SourceHealth:
    source: Source
    status: str  # working | partial | failing | not run | not covered
    papers: int
    with_abstract: int
    last_run: dict | None
    last_success: str | None

    @property
    def abstract_share(self) -> float | None:
        return self.with_abstract / self.papers if self.papers else None


def source_health(conn: sqlite3.Connection, sources: list[Source]) -> list[SourceHealth]:
    counts = {
        row["source_id"]: (row["papers"], row["with_abstract"])
        for row in conn.execute(
            "SELECT source_id, COUNT(*) AS papers, SUM(length(abstract) >= ?) AS with_abstract"
            " FROM papers GROUP BY source_id",
            (MIN_ABSTRACT_CHARS,),
        )
    }
    last_runs = {
        row["source_id"]: dict(row)
        for row in conn.execute(
            """SELECT r.* FROM source_runs r
               JOIN (SELECT source_id, MAX(id) AS id FROM source_runs GROUP BY source_id) last ON last.id = r.id"""
        )
    }
    last_success = dict(conn.execute(
        "SELECT source_id, MAX(started_at) FROM source_runs WHERE status = 'ok' GROUP BY source_id"
    ).fetchall())

    report = []
    for s in sources:
        papers, with_abstract = counts.get(s.id, (0, 0))
        with_abstract = with_abstract or 0
        run = last_runs.get(s.id)
        if not s.enabled:
            status = "not covered"
        elif run is None:
            status = "not run"
        elif run["status"] != "ok":
            status = "failing"
        elif papers and with_abstract / papers < PARTIAL_BELOW:
            status = "partial"
        else:
            status = "working"
        report.append(SourceHealth(s, status, papers, with_abstract, run, last_success.get(s.id)))
    return report
