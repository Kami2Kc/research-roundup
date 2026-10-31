"""End-to-end with FakeLLM and saved responses: collect -> screen -> build issue -> newsletter -> export."""

import json
from datetime import date

from roundup import editor, export, newsletter
from roundup.collectors import collect_all
from roundup.editor import FAKE_RESPONDERS as EDITOR_FAKES
from roundup.llm import FakeLLM
from roundup.screening import FAKE_RESPONDERS as SCREENING_FAKES, screen_papers
from tests.test_collectors import ECB, NBER, NY_FED


def test_end_to_end(conn, http, tmp_path):
    sources = [NBER, ECB, NY_FED]
    by_id = {s.id: s for s in sources}
    results = collect_all(conn, sources, http, date(2026, 9, 1))
    assert all(r.status == "ok" for r in results), results

    llm = FakeLLM({**SCREENING_FAKES, **EDITOR_FAKES})
    stats = screen_papers(conn, llm, "fake", by_id, limit=100)
    assert stats.screened > 10

    issue = editor.build_issue(conn, llm, "fake", "2026-10", by_id, threshold=0)
    assert 5 <= len(issue.papers) <= 8
    assert {p["market_focus"] for p in issue.papers} == {"EM", "DM", "Transversal"}

    path = newsletter.write(conn, issue, sources_monitored=3, out_dir=tmp_path / "newsletters")
    html = path.read_text()
    assert "The Research Roundup" in html and "October 2026" in html
    assert "<script" not in html.lower()
    assert 'style="' in html  # CSS was inlined
    assert "@media" in html  # mobile rules kept
    if any(p["paywalled"] for p in issue.papers):
        assert "Summary based on abstract" in html

    # Re-rendering from the database gives the same newsletter without calling the editor.
    calls_before = len(llm.calls)
    assert newsletter.render(newsletter.load_issue(conn, "2026-10", by_id), 1, 3) == newsletter.render(issue, 1, 3)
    assert len(llm.calls) == calls_before

    counts = export.export_all(conn, sources, out_dir=tmp_path / "data")
    issues = json.loads((tmp_path / "data" / "issues.json").read_text())
    papers = json.loads((tmp_path / "data" / "papers.json").read_text())
    assert counts["issues"] == 1 and issues[0]["month"] == "2026-10"
    in_issue = [p for p in papers if p["issues"] == ["2026-10"]]
    assert len(in_issue) == len(issue.papers)
    assert {p["slug"] for p in in_issue} == {e["slug"] for e in issues[0]["papers"]}


def test_selection_check_catches_rule_breaks(conn, http):
    collect_all(conn, [ECB], http, date(2026, 9, 1))
    screen_papers(conn, FakeLLM(SCREENING_FAKES), "fake", {"ecb": ECB}, limit=100)
    pool = editor.candidate_pool(conn, "2026-10", threshold=0)
    too_few = editor.Selection(picks=[editor.Pick(paper_id=pool[0]["id"], reason="r")], rationale="r")
    problems = editor.check_selection(too_few, pool)
    assert any("Choose between" in p for p in problems)
    bad_id = editor.Selection(picks=[editor.Pick(paper_id="nope", reason="r")] * 5, rationale="r")
    assert any("not in the candidate list" in p for p in editor.check_selection(bad_id, pool))


def add_screened(conn, paper_id, focus, relevance, source_id="ecb", topic="monetary policy", abstract_len=600):
    from roundup import db as roundup_db
    from tests.test_db import make_paper
    roundup_db.upsert_papers(conn, [make_paper(id=paper_id, source_id=source_id, abstract="x" * abstract_len)])
    roundup_db.save_screening(conn, paper_id, "screened", model="test", prompt_version="test", result={
        "relevance_score": relevance, "market_focus": focus, "focus_rationale": "r", "topics": [topic], "regions": []})


def test_pool_reserves_places_for_each_focus_and_skips_thin_abstracts(conn):
    for i in range(50):
        add_screened(conn, f"dm{i}", "DM", 10)
    add_screened(conn, "em1", "EM", 6)
    add_screened(conn, "tr1", "Transversal", 7)
    add_screened(conn, "thin", "EM", 9, abstract_len=150)
    pool = editor.candidate_pool(conn, "2026-10", threshold=6)
    ids = {row["id"] for row in pool}
    assert len(pool) == editor.POOL_CAP
    assert {"em1", "tr1"} <= ids  # lower-scored, but reserved places keep them in
    assert "thin" not in ids


def test_selection_rules_on_balance_sources_and_topics(conn):
    for i in range(4):
        add_screened(conn, f"dm{i}", "DM", 9, source_id="ecb" if i < 3 else "boe", topic="inflation")
        add_screened(conn, f"em{i}", "EM", 8, source_id="imf", topic="fx and capital flows")
        add_screened(conn, f"tr{i}", "Transversal", 8, source_id=f"src{i}", topic="other")
    pool = editor.candidate_pool(conn, "2026-10", threshold=6)
    picks = ["dm0", "dm1", "dm2", "dm3", "em0", "tr0"]
    problems = editor.check_selection(
        editor.Selection(picks=[editor.Pick(paper_id=i, reason="r") for i in picks], rationale="r"), pool)
    joined = " ".join(problems)
    assert "no more than half" in joined  # 4 of 6 are DM
    assert "share a source" in joined  # three from the ECB
    assert "main topic 'inflation'" in joined
    good = ["dm0", "dm3", "em0", "em1", "tr0", "tr1"]
    assert editor.check_selection(
        editor.Selection(picks=[editor.Pick(paper_id=i, reason="r") for i in good], rationale="r"), pool) == []


def test_draft_word_limits_are_checked():
    long_summary = "word " * 200
    draft = editor.IssueDraft(editor_note="Too short.", papers=[editor.Writeup(
        paper_id="p1", headline="A perfectly reasonable headline here", summary=long_summary,
        takeaways=["a", "b", "c"], why_it_matters="word " * 40, market_focus="DM", focus_rationale="r")])
    problems = editor.check_draft(draft, ["p1"])
    assert any("editor's note" in p for p in problems)
    assert any("summary has 200 words" in p for p in problems)
