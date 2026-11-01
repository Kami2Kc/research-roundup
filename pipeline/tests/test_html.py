from datetime import date

import httpx
import pytest

from roundup.collectors import apply_filters, collect_source, html
from roundup.collectors.base import HttpClient
from roundup.models import Paper, Source
from tests.conftest import FIXTURES

BOJ = Source(id="boj", name="Bank of Japan", group="g10_cb", country_or_region="Japan", method="html",
             url="https://www.boj.or.jp/en/research/rs_all_{year}/index.htm", link_pattern="/research/wps_rev/",
             selectors={"item": "tbody tr", "title": "td a", "date": "td"})
BDF = Source(id="bdf", name="Banque de France", group="g10_cb", country_or_region="France", method="html",
             url="https://www.banque-france.fr/wp", selectors={"item": "a.card.card-vertical", "title": "h3.card-title",
                                                                "date": "small"})
HNB = Source(id="hnb", name="HNB", group="european_ncb", country_or_region="Croatia", method="html",
             url="https://www.hnb.hr/wp", selectors={"item": "div.entry-container", "title": "h4.title a",
                                                     "date": "tr:nth-of-type(2) td", "authors": "tr:nth-of-type(4) td"})
BDI = Source(id="bancaditalia", name="Banca d'Italia", group="g10_cb", country_or_region="Italy", method="html",
             url="https://www.bancaditalia.it/temi", title_strip=r"^No\.\s*\d+\s*-\s*",
             selectors={"item": "div.bdi-ultime-pubblicazioni li", "title": "a.bdi-ultime-pubblicazioni-title",
                        "date": ".bdi-ultime-pubblicazioni-date", "authors": ".bdi-ultime-pubblicazioni-first",
                        "abstract": "div.bdi-main-column div.bdi-typography"})


def handler(request: httpx.Request) -> httpx.Response:
    host, path = request.url.host, request.url.path
    if path == "/robots.txt":
        return httpx.Response(404)
    if host == "www.boj.or.jp":
        name = "html_boj_list.html"
    elif host == "www.bancaditalia.it":
        name = "html_bdi_paper.html" if "/2026/" in path else "html_bdi_list.html"
    else:
        name = {"www.banque-france.fr": "html_bdf_list.html", "www.hnb.hr": "html_hnb_list.html"}.get(host)
    if name is None:
        return httpx.Response(404)
    return httpx.Response(200, content=(FIXTURES / name).read_bytes())


@pytest.fixture
def http() -> HttpClient:
    return HttpClient("test@example.org", min_interval=0, transport=httpx.MockTransport(handler))


@pytest.mark.parametrize("text, expected", [
    ("7th of October 2026", date(2026, 10, 7)),
    ("Sept. 25, 2026", date(2026, 9, 25)),
    ("Oct. 8, 2026", date(2026, 10, 8)),
    ("21/09/2026", date(2026, 9, 21)),
    ("20 October 2026", date(2026, 10, 20)),
    ("July 2026", date(2026, 7, 1)),
    ("2026-10-30", date(2026, 10, 30)),
    ("30.10.2026", date(2026, 10, 30)),
    ("not a date", None),
])
def test_parse_date(text, expected):
    assert html.parse_date(text) == expected


def test_boj_listing_keeps_only_research_papers(http):
    papers = html.collect(BOJ, http, date(2026, 1, 1))
    kept = apply_filters(BOJ, papers, date(2026, 1, 1))
    assert len(kept) < len(papers)  # reports and data releases are dropped
    assert kept and all("/research/wps_rev/" in p.url and p.published_date for p in kept)


def test_bdf_cards_with_ordinal_dates(http):
    papers = html.collect(BDF, http, date(2026, 1, 1))
    assert len(papers) == 12
    assert papers[0].title == "DSGE Models in Central Banks: Progress and Prospects"
    assert papers[0].published_date == date(2026, 10, 7)
    assert papers[0].url.startswith("https://www.banque-france.fr/en/publications-and-statistics/publications/")


def test_hnb_month_dates_and_authors_from_a_table(http):
    papers = html.collect(HNB, http, date(2026, 1, 1))
    first = papers[0]
    assert first.published_date == date(2026, 7, 1)
    assert first.authors == ["Karlo Kotarac", "Davor Kunovac", "Ozana Nadoveza"]


def test_abstract_from_the_paper_page_and_title_cleanup(conn, http):
    result = collect_source(conn, BDI, http, date(2026, 8, 1))
    assert result.status == "ok" and result.new == 6
    row = conn.execute("SELECT * FROM papers WHERE title LIKE 'Beyond firm size%'").fetchone()
    assert row is not None  # "No. 1549 - " was stripped
    assert row["abstract"].startswith("This paper compares supplier networks")
    assert "M. Saldias" in row["authors"]


def test_abstract_prefixes_are_removed():
    text = "doi.org/10.71734/DP-2026-34 Why did the US dollar depreciate?"
    assert html.ABSTRACT_PREFIX.sub("", text) == "Why did the US dollar depreciate?"


def test_page_abstract_stops_where_the_article_body_starts():
    end = "h2, p:nth-of-type(3)"
    page = ('<main><div class="richtext"><p>doi.org/10.71734/DP-2026-34</p><p>Why did the dollar fall?</p>'
            "<h2>A tariff shock</h2><p>We study the announcement.</p><p>References</p></div></main>")
    assert html.page_abstract(page, "main div.richtext", end) == "Why did the dollar fall?"
    assert html.page_abstract(page, "main div.richtext").endswith("References")
    no_heading = page.replace("<h2>A tariff shock</h2>", "")  # the summary can start straight after the abstract
    assert html.page_abstract(no_heading, "main div.richtext", end) == "Why did the dollar fall?"


def test_authors_are_taken_from_the_title_suffix():
    bundesbank = Source(id="bundesbank", name="Bundesbank", group="g10_cb", country_or_region="Germany",
                        method="rss", feed_urls=["https://example.org/feed"],
                        title_strip=r"\s*\|\s*(?P<authors>.*)$")
    paper = Paper(id="url:1", source_id="bundesbank", url="https://example.org/p",
                       title="What volatility reveals | Lucas ter Steege, Sofia Velasco",
                       fetched_at="2026-11-01T00:00:00Z")
    [kept] = apply_filters(bundesbank, [paper], date(2026, 8, 1))
    assert kept.title == "What volatility reveals"
    assert kept.authors == ["Lucas ter Steege", "Sofia Velasco"]


def test_undated_listing_is_dated_on_first_sight_after_the_first_run(conn):
    pages = iter([
        '<ul><li><a href="/p/1">Paper one</a></li></ul>',
        '<ul><li><a href="/p/2">Paper two</a></li><li><a href="/p/1">Paper one</a></li></ul>',
    ])
    current = {"page": ""}

    def listing(request):
        if request.url.path == "/robots.txt":
            return httpx.Response(404)
        return httpx.Response(200, text=current["page"])

    source = Source(id="mnb", name="MNB", group="european_ncb", country_or_region="Hungary", method="html",
                    url="https://example.org/wp", selectors={"item": "li a"})
    client = HttpClient("test@example.org", min_interval=0, transport=httpx.MockTransport(listing))
    for _ in range(2):
        current["page"] = next(pages)
        collect_source(conn, source, client, date(2026, 8, 1))
    dates = dict(conn.execute("SELECT title, published_date FROM papers").fetchall())
    assert dates == {"Paper one": None, "Paper two": date.today().isoformat()}
