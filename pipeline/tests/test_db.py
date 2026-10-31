from datetime import date, datetime, timezone

from roundup import db
from roundup.models import Paper


def make_paper(**overrides) -> Paper:
    fields = dict(id="10.1/abc", source_id="ecb", title="A paper", url="https://x.org/a",
                  published_date=date(2026, 10, 1), fetched_at=datetime.now(timezone.utc))
    return Paper(**{**fields, **overrides})


def test_upsert_is_idempotent(conn):
    papers = [make_paper(id="10.1/a"), make_paper(id="10.1/b")]
    assert db.upsert_papers(conn, papers) == 2
    assert db.upsert_papers(conn, papers) == 0
    assert conn.execute("SELECT COUNT(*) FROM papers").fetchone()[0] == 2


def test_upsert_fills_an_abstract_that_arrives_later(conn):
    db.upsert_papers(conn, [make_paper(abstract=None)])
    db.upsert_papers(conn, [make_paper(abstract="Now we have one.")])
    assert conn.execute("SELECT abstract FROM papers").fetchone()[0] == "Now we have one."


def test_upsert_never_overwrites_a_full_abstract(conn):
    full = "An abstract long enough to count as complete. " * 8
    db.upsert_papers(conn, [make_paper(abstract=full)])
    db.upsert_papers(conn, [make_paper(abstract=full + " Something longer.")])
    assert conn.execute("SELECT abstract FROM papers").fetchone()[0] == full


def test_upsert_replaces_a_short_teaser_with_a_longer_abstract(conn):
    db.upsert_papers(conn, [make_paper(abstract="A one-line teaser from the feed.")])
    db.upsert_papers(conn, [make_paper(abstract="The full abstract from the paper's own page. " * 3)])
    assert conn.execute("SELECT abstract FROM papers").fetchone()[0].startswith("The full abstract")
