"""RSS/Atom feeds, parsed with feedparser."""

from datetime import date, datetime, timezone

import feedparser

from roundup.collectors.base import HttpClient, clean_text
from roundup.models import Paper, Source, make_paper_id

# Feeds put a DOI in different places (Fed in Print uses identifiers_doi).
DOI_KEYS = ("identifiers_doi", "prism_doi", "dc_identifier")


def collect(source: Source, http: HttpClient, since: date) -> list[Paper]:
    """Every item in the source's feeds. Feeds can't be queried by date; the caller filters on `since`."""
    papers = []
    for feed_url in source.feed_urls:
        feed = feedparser.parse(http.get(feed_url).content)
        if feed.bozo and not feed.entries:
            raise ValueError(f"could not parse feed {feed_url}: {feed.bozo_exception}")
        papers.extend(p for p in (parse_entry(e, source, feed_url) for e in feed.entries) if p)
    return papers


def split_names(field: str) -> list[str]:
    """Fed in Print sends "King, Thomas B.; Feldman, Corey": split on ';' and turn "Last, First" into "First Last"."""
    names = []
    for name in (n.strip() for n in field.split(";")):
        last, sep, first = name.partition(", ")
        if sep and first and "," not in first and first.rstrip(".") not in ("Jr", "Sr", "II", "III"):
            name = f"{first} {last}"
        if name:
            names.append(name)
    return names


def parse_entry(entry: dict, source: Source, feed_url: str) -> Paper | None:
    title = clean_text(entry.get("title"))
    link = entry.get("link")
    if not title or not link:
        return None
    doi = next((entry[k] for k in DOI_KEYS if str(entry.get(k, "")).startswith("10.")), None)
    parsed = entry.get("published_parsed") or entry.get("updated_parsed")
    return Paper(
        id=make_paper_id(doi, link),
        source_id=source.id,
        title=title,
        authors=[name for a in entry.get("authors", []) for name in split_names(a.get("name", ""))],
        abstract=clean_text(entry.get("summary")) or None,
        url=link,
        published_date=date(parsed.tm_year, parsed.tm_mon, parsed.tm_mday) if parsed else None,  # UTC
        paywalled=source.paywalled,
        fetched_at=datetime.now(timezone.utc),
        raw_meta={
            "feed": feed_url,
            "doi": doi.lower() if doi else None,
            "series": entry.get("bibo_series"),
            "abstract_source": "feed" if entry.get("summary") else None,
        },
    )
