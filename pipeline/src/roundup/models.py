"""Data models shared across the pipeline."""

from enum import StrEnum

from pydantic import BaseModel, model_validator


class Group(StrEnum):
    JOURNAL = "journal"
    G10_CB = "g10_cb"
    FED_REGIONAL = "fed_regional"
    EUROPEAN_NCB = "european_ncb"
    INTL_ORG = "intl_org"
    NBER = "nber"
    BPEA = "bpea"


class Method(StrEnum):
    CROSSREF = "crossref"
    OPENALEX = "openalex"
    RSS = "rss"
    HTML = "html"
    NONE = "none"  # listed for coverage reporting, but not collected


class Source(BaseModel):
    """One entry in config/sources.yaml."""

    id: str
    name: str
    group: Group
    country_or_region: str
    method: Method
    url: str | None = None  # the source's own listing page
    feed_urls: list[str] = []
    issns: list[str] = []  # crossref/openalex: query by journal or series ISSN
    doi_prefix: str | None = None  # crossref: query by DOI prefix instead (e.g. NBER)
    link_pattern: str | None = None  # regex: keep only feed items whose link matches
    exclude_pattern: str | None = None  # regex: drop items whose title or series matches
    selectors: dict[str, str] | None = None
    fallback: Method | None = None
    paywalled: bool = False
    enabled: bool = True
    notes: str = ""

    @model_validator(mode="after")
    def check_method_settings(self) -> "Source":
        if self.method == Method.NONE and self.enabled:
            raise ValueError(f"{self.id}: method 'none' must have enabled: false")
        if not self.enabled:
            return self  # disabled sources may be planned but not yet configured
        if self.method in (Method.CROSSREF, Method.OPENALEX) and not (self.issns or self.doi_prefix):
            raise ValueError(f"{self.id}: method '{self.method}' needs ISSNs or a DOI prefix")
        if self.method == Method.RSS and not self.feed_urls:
            raise ValueError(f"{self.id}: method 'rss' needs at least one feed URL")
        if self.method == Method.HTML and not (self.url and self.selectors):
            raise ValueError(f"{self.id}: method 'html' needs a url and selectors")
        return self
