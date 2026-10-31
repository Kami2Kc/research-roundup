"""OpenAlex: fills in abstracts that Crossref doesn't have, looked up by DOI in batches."""

from roundup.collectors.base import HttpClient
from roundup.models import Paper

API = "https://api.openalex.org/works"
BATCH = 50  # OpenAlex accepts up to 50 values in one OR filter


def fill_abstracts(papers: list[Paper], http: HttpClient) -> int:
    """Add OpenAlex abstracts to papers that have a DOI but no abstract. Returns how many were filled."""
    missing = [p for p in papers if not p.abstract and p.raw_meta.get("doi")]
    filled = 0
    for start in range(0, len(missing), BATCH):
        batch = missing[start:start + BATCH]
        params = {
            "filter": "doi:" + "|".join(p.raw_meta["doi"] for p in batch),
            "per-page": BATCH,
            "select": "doi,abstract_inverted_index",
            "mailto": http.contact_email,
        }
        abstracts = {}
        for work in http.get(API, params=params).json().get("results", []):
            if work.get("doi") and work.get("abstract_inverted_index"):
                doi = work["doi"].lower().removeprefix("https://doi.org/")
                abstracts[doi] = rebuild_abstract(work["abstract_inverted_index"])
        for p in batch:
            if abstracts.get(p.raw_meta["doi"]):
                p.abstract = abstracts[p.raw_meta["doi"]]
                p.raw_meta["abstract_source"] = "openalex"
                filled += 1
    return filled


def rebuild_abstract(inverted_index: dict[str, list[int]]) -> str:
    """OpenAlex stores abstracts as {word: [positions]}; put the words back in order."""
    positions = {pos: word for word, places in inverted_index.items() for pos in places}
    return " ".join(positions[i] for i in sorted(positions))
