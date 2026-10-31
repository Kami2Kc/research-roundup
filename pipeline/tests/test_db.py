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


def test_upsert_never_overwrites_an_existing_abstract(conn):
    db.upsert_papers(conn, [make_paper(abstract="Original.")])
    db.upsert_papers(conn, [make_paper(abstract="Different.")])
    assert conn.execute("SELECT abstract FROM papers").fetchone()[0] == "Original."
