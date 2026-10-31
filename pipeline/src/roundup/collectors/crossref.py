"""Crossref REST API: journals (by ISSN) and working-paper series (by ISSN or DOI prefix).

We filter on the DOI registration date (`from-created-date`), not the publication date:
some journals deposit year-only dates (Econometrica) or future issue dates (AER), which a
publication-date filter would miss or misdate.
"""

import re
from datetime import date, datetime, timezone

from roundup.collectors.base import HttpClient, clean_text
from roundup.models import Paper, Source, make_paper_id

API = "https://api.crossref.org"
FIELDS = "DOI,title,author,abstract,URL,created,published-online,published-print,issued,type,container-title"
PAGE_SIZE = 100
MAX_PAGES = 20

# Journal housekeeping that would otherwise be logged as "no abstract".
NON_RESEARCH_TITLE = re.compile(
    r"^(front ?matter|back ?matter|announcements?|editorial|report of the|.*turnaround times|submission of manuscripts"
    r"|forthcoming papers|errat(um|a)|corrigendum|correction|index|list of referees|referees|retraction)\b",
    re.IGNORECASE,
)


def collect(source: Source, http: HttpClient, since: date) -> list[Paper]:
    filters = [f"from-created-date:{since.isoformat()}"]
    if source.issns:
        url = f"{API}/journals/{source.issns[0]}/works"
    else:
        url = f"{API}/works"
        filters.append(f"prefix:{source.doi_prefix}")

    params = {"filter": ",".join(filters), "rows": PAGE_SIZE, "select": FIELDS,
              "mailto": http.contact_email, "cursor": "*"}
    papers: list[Paper] = []
    for _ in range(MAX_PAGES):
        message = http.get(url, params=params).json()["message"]
        items = message["items"]
        papers.extend(p for p in (parse_item(item, source) for item in items) if p)
        if len(items) < PAGE_SIZE or not message.get("next-cursor"):
            break
        params["cursor"] = message["next-cursor"]
    return papers


def parse_item(item: dict, source: Source) -> Paper | None:
    title = clean_text((item.get("title") or [""])[0])
    if not title or NON_RESEARCH_TITLE.match(title):
        return None
    doi = item["DOI"].lower()
    abstract = clean_text(item.get("abstract"))
    abstract = re.sub(r"^abstract\s*:?\s*", "", abstract, flags=re.IGNORECASE)
    authors = [
        " ".join(filter(None, [a.get("given"), a.get("family")])) or a.get("name", "")
        for a in item.get("author", [])
    ]
    return Paper(
        id=make_paper_id(doi, item.get("URL", "")),
        source_id=source.id,
        title=title,
        authors=[a for a in authors if a],
        abstract=abstract or None,
        url=item.get("URL") or f"https://doi.org/{doi}",
        published_date=earliest_date(item),
        paywalled=source.paywalled,
        fetched_at=datetime.now(timezone.utc),
        raw_meta={
            "doi": doi,
            "type": item.get("type"),
            "container": (item.get("container-title") or [None])[0],
            "abstract_source": "crossref" if abstract else None,
        },
    )


def earliest_date(item: dict) -> date | None:
    """The earliest full (year-month-day) date Crossref gives: online, print, issue or registration."""
    candidates = []
    for key in ("published-online", "published-print", "issued", "created"):
        parts = (item.get(key) or {}).get("date-parts") or [[]]
        if len(parts[0]) == 3:
            candidates.append(date(*parts[0]))
    return min(candidates) if candidates else None
