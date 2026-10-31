from datetime import date

import httpx

from roundup.collectors import apply_filters, collect_all, crossref, openalex, rss
from roundup.collectors.base import HttpClient, RobotsDisallowed
from roundup.models import Source, make_paper_id, normalise_url

SINCE = date(2026, 8, 1)

ECONOMETRICA = Source(id="econometrica", name="Econometrica", group="journal", country_or_region="Intl",
                      method="crossref", issns=["0012-9682"], fallback="openalex", paywalled=True)
NBER = Source(id="nber", name="NBER", group="nber", country_or_region="US", method="crossref",
              doi_prefix="10.3386", fallback="openalex", paywalled=True)
ECB = Source(id="ecb", name="ECB", group="g10_cb", country_or_region="Euro area", method="rss",
             feed_urls=["https://www.ecb.europa.eu/rss/wppub.html"])
NY_FED = Source(id="ny_fed", name="New York Fed", group="fed_regional", country_or_region="US", method="rss",
                feed_urls=["https://www.fedinprint.org/rss/newyork.rss"], exclude_pattern="(?i)speech|remarks")
BOE = Source(id="boe", name="Bank of England", group="g10_cb", country_or_region="UK", method="rss",
             feed_urls=["https://www.bankofengland.co.uk/rss/publications"], link_pattern="/working-paper/")


def test_crossref_uses_registration_date_when_publication_date_is_year_only(http):
    papers = crossref.collect(ECONOMETRICA, http, SINCE)
    assert len(papers) == 6
    p = papers[0]
    assert p.id == "10.3982/ecta23242"
    assert p.published_date == date(2026, 9, 14)  # Crossref only says "2026"; created date is 14 Sep
    assert p.abstract and not p.abstract.startswith("<")  # JATS tags stripped
    assert p.paywalled and p.authors[0] == "Ulrich Müller"


def test_earliest_date_prefers_the_earliest_full_date():
    item = {"issued": {"date-parts": [[2026, 11, 1]]}, "published-print": {"date-parts": [[2026, 11, 1]]},
            "created": {"date-parts": [[2026, 10, 30]]}, "published-online": {"date-parts": [[2026, 10]]}}
    assert crossref.earliest_date(item) == date(2026, 10, 30)


def test_crossref_skips_journal_housekeeping():
    item = {"DOI": "10.1/x", "title": ["Front Matter"], "created": {"date-parts": [[2026, 10, 1]]}}
    assert crossref.parse_item(item, ECONOMETRICA) is None


def test_openalex_fills_missing_nber_abstracts(http):
    papers = crossref.collect(NBER, http, SINCE)
    assert papers and all(p.abstract is None for p in papers)  # Crossref has no NBER abstracts
    assert openalex.fill_abstracts(papers, http) == len(papers)
    assert all(p.abstract and p.raw_meta["abstract_source"] == "openalex" for p in papers)


def test_rebuild_abstract_from_inverted_index():
    assert openalex.rebuild_abstract({"rates": [2], "Higher": [0], "interest": [1]}) == "Higher interest rates"


def test_rss_parses_ecb_working_papers(http):
    papers = rss.collect(ECB, http, SINCE)
    assert len(papers) == 15
    assert all(p.published_date and p.abstract for p in papers)
    assert papers[0].id.startswith("url:")  # no DOI in this feed


def test_fed_in_print_carries_dois_and_speeches_are_filtered(http):
    papers = rss.collect(NY_FED, http, SINCE)
    assert any(p.id.startswith("10.") for p in papers)
    kept = apply_filters(NY_FED, papers, SINCE)
    assert len(kept) < len(papers)
    assert not any("speech" in (p.raw_meta.get("series") or "").lower() for p in kept)


def test_link_pattern_keeps_only_boe_working_papers(http):
    kept = apply_filters(BOE, rss.collect(BOE, http, SINCE), date(2000, 1, 1))
    assert kept and all("/working-paper/" in p.url for p in kept)


def test_since_drops_older_items(http):
    papers = rss.collect(ECB, http, SINCE)
    kept = apply_filters(ECB, papers, date(2026, 10, 1))
    assert kept and all(p.published_date >= date(2026, 10, 1) for p in kept)


def test_one_failing_source_does_not_stop_the_run(conn, http):
    broken = Source(id="broken", name="Broken", group="g10_cb", country_or_region="X", method="rss",
                    feed_urls=["https://example.org/missing.xml"])
    results = collect_all(conn, [broken, ECB], http, SINCE)
    assert [r.status for r in results] == ["error", "ok"]
    assert results[1].new == 15
    assert conn.execute("SELECT COUNT(*) FROM source_runs").fetchone()[0] == 2


def test_robots_txt_is_respected():
    def handler(request):
        if request.url.path == "/robots.txt":
            return httpx.Response(200, text="User-agent: *\nDisallow: /private/")
        return httpx.Response(200, text="ok")

    client = HttpClient("test@example.org", min_interval=0, transport=httpx.MockTransport(handler))
    assert client.get("https://example.org/public/feed.xml").text == "ok"
    try:
        client.get("https://example.org/private/feed.xml")
        raise AssertionError("expected RobotsDisallowed")
    except RobotsDisallowed:
        pass


def test_retries_on_server_errors(monkeypatch):
    monkeypatch.setattr("time.sleep", lambda s: None)
    calls = {"n": 0}

    def handler(request):
        if request.url.path == "/robots.txt":
            return httpx.Response(404)
        calls["n"] += 1
        return httpx.Response(503) if calls["n"] < 3 else httpx.Response(200, text="ok")

    client = HttpClient("test@example.org", min_interval=0, transport=httpx.MockTransport(handler))
    assert client.get("https://example.org/feed.xml").text == "ok"
    assert calls["n"] == 3


def test_paper_ids():
    assert make_paper_id("10.3386/W35838", "https://x") == "10.3386/w35838"
    assert normalise_url("HTTPS://WWW.ECB.europa.eu//pub/a.pdf#top") == "https://www.ecb.europa.eu/pub/a.pdf"
    assert make_paper_id(None, "https://a.org/x/") == make_paper_id(None, "https://A.org//x")


def test_fed_in_print_author_names_are_normalised():
    assert rss.split_names("King, Thomas B.; Feldman, Corey") == ["Thomas B. King", "Corey Feldman"]
    assert rss.split_names("Jane Smith") == ["Jane Smith"]
    assert rss.split_names("Smith, Jr.") == ["Smith, Jr."]
