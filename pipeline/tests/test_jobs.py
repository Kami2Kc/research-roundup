import json
from datetime import date

from roundup import jobs
from roundup.config import Settings
from roundup.editor import FAKE_RESPONDERS as EDITOR_FAKES
from roundup.llm import FakeLLM
from roundup.screening import FAKE_RESPONDERS as SCREENING_FAKES
from tests.test_collectors import ECB, NBER, NY_FED

SETTINGS = Settings(llm_provider="fake", llm_api_key=None, llm_screen_model="fake", llm_editor_model="fake",
                    contact_email="test@example.org", screen_limit=300, relevance_threshold=0, site_url=None)


def make_context(conn, http, tmp_path) -> jobs.Context:
    return jobs.Context(conn, SETTINGS, [NBER, ECB, NY_FED], http, FakeLLM({**SCREENING_FAKES, **EDITOR_FAKES}),
                        web_public=tmp_path)


def test_previous_month_and_month_ranges():
    assert jobs.previous_month(date(2026, 11, 1)) == "2026-10"
    assert jobs.previous_month(date(2027, 1, 15)) == "2026-12"
    assert jobs.months_between(date(2026, 8, 1), date(2026, 10, 31)) == ["2026-08", "2026-09", "2026-10"]


def test_backfill_builds_each_month_once_and_skips_empty_ones(conn, http, tmp_path):
    ctx = make_context(conn, http, tmp_path)
    report = jobs.backfill(ctx, date(2026, 7, 1), date(2026, 10, 31), limit=500)
    built = [issue.month for issue in report.issues]
    assert "2026-10" in built and "2026-07" not in built  # July has no papers in the fixtures: skipped, not fatal
    assert (tmp_path / "newsletters" / "2026-10.html").exists()
    assert json.loads((tmp_path / "data" / "issues.json").read_text())[0]["month"] == built[-1]

    again = jobs.backfill(ctx, date(2026, 7, 1), date(2026, 10, 31), limit=500)
    assert again.issues == []  # existing issues are kept unless rebuild=True
    # (FakeLLM's placeholder screenings are redone by design; the never-re-screen rule is tested in test_screening)


def test_weekly_job_collects_screens_and_exports(conn, http, tmp_path):
    report = jobs.run_weekly(make_context(conn, http, tmp_path), today=date(2026, 10, 31))
    assert all(r.status == "ok" for r in report.collected)
    assert report.screened.screened > 0 and not report.all_sources_failed
    assert (tmp_path / "data" / "papers.json").exists()
