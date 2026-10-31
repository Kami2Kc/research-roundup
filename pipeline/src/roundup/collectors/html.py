"""HTML listing pages, driven by CSS selectors in config/sources.yaml, plus abstracts from each paper's own page.

Selectors for a listing page (method: html):
  item      each paper on the listing page (required)
  title     element inside the item holding the title (default: the item itself)
  link      element inside the item whose href is the paper's URL (default: the item or title if it is a link,
            otherwise the first link in the item)
  date      element inside the item holding the publication date (optional; see below)
  authors   element inside the item listing the authors (optional)
Selector for the paper's own page (method: html or rss):
  abstract  element(s) holding the abstract; the longest match is used

Listings without dates get the date we first saw the paper (see collectors/__init__.py).
A listing URL may contain {year}, replaced by the current year.
"""

import re
from datetime import date, datetime, timezone
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from roundup.collectors.base import HttpClient, clean_text
from roundup.db import FULL_ABSTRACT_CHARS
from roundup.models import Paper, Source, make_paper_id

DATE_FORMATS = ("%d %B %Y", "%d %b %Y", "%B %d, %Y", "%b %d, %Y", "%d/%m/%Y", "%d.%m.%Y", "%Y-%m-%d", "%B %Y", "%b %Y")
# Boilerplate some banks put before the abstract: "Abstract:", "doi.org/10.71734/DP-2026-34", "Working Paper Series no. 1066."
ABSTRACT_PREFIX = re.compile(r"^(?:abstract\s*:?|doi\.org/\S+|working paper series no\.\s*\d+\s*\.)\s*", re.IGNORECASE)


def collect(source: Source, http: HttpClient, since: date) -> list[Paper]:
    sel = source.selectors or {}
    response = http.get(source.url.format(year=date.today().year))  # some listings are one page per year
    soup = BeautifulSoup(response.text, "html.parser")
    papers = []
    for item in soup.select(sel["item"]):
        title_el = item.select_one(sel["title"]) if sel.get("title") else item
        link_el = item.select_one(sel["link"]) if sel.get("link") else _default_link(item, title_el)
        if title_el is None or link_el is None or not link_el.get("href"):
            continue
        url = urljoin(str(response.url), link_el["href"])
        date_el = item.select_one(sel["date"]) if sel.get("date") else None
        authors_el = item.select_one(sel["authors"]) if sel.get("authors") else None
        papers.append(Paper(
            id=make_paper_id(None, url),
            source_id=source.id,
            title=clean_text(title_el.get_text(" ")),
            authors=split_authors(authors_el.get_text(" ")) if authors_el else [],
            url=url,
            published_date=parse_date(date_el.get("datetime") or date_el.get_text(" ")) if date_el else None,
            paywalled=source.paywalled,
            fetched_at=datetime.now(timezone.utc),
            raw_meta={"listing": source.url, "undated": not sel.get("date")},
        ))
    return papers


def _default_link(item, title_el):
    for el in (item, title_el):
        if el is not None and el.name == "a":
            return el
    return (title_el.find("a") if title_el is not None else None) or item.find("a")


def fill_abstracts(papers: list[Paper], http: HttpClient, selector: str) -> int:
    """Take the abstract from each paper's own page when we have none, or only a short teaser."""
    filled = 0
    for p in papers:
        if (p.abstract and len(p.abstract) >= FULL_ABSTRACT_CHARS) or p.url.lower().endswith(".pdf"):
            continue
        soup = BeautifulSoup(http.get(p.url).text, "html.parser")
        texts = [clean_text(el.get_text(" ")) for el in soup.select(selector)]
        best = max(texts, key=len, default="")
        while (stripped := ABSTRACT_PREFIX.sub("", best)) != best:
            best = stripped
        if len(best) > len(p.abstract or ""):
            p.abstract = best
            p.raw_meta["abstract_source"] = "page"
            filled += 1
    return filled


def parse_date(text: str) -> date | None:
    """Parse the date formats central banks use, e.g. '7th of October 2026', 'Sept. 25, 2026', '21/09/2026'."""
    text = clean_text(text)
    text = re.sub(r"(\d)(st|nd|rd|th)\b", r"\1", text)
    text = re.sub(r"\bof\b", " ", text).replace(".", " ").replace("Sept ", "Sep ")
    text = " ".join(text.split()).replace(" ,", ",")
    if re.fullmatch(r"\d{1,2} \d{1,2} \d{4}", text):  # "21.09.2026" after the dots were removed
        text = text.replace(" ", ".")
    for fmt in DATE_FORMATS:
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    return None


def split_authors(text: str) -> list[str]:
    text = re.sub(r"^\s*by\s+", "", clean_text(text), flags=re.IGNORECASE)
    return [a.strip() for a in re.split(r",\s*|\s+and\s+", text) if a.strip()]
