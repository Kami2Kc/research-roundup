from pathlib import Path

import httpx
import pytest

from roundup import db
from roundup.collectors.base import HttpClient

FIXTURES = Path(__file__).parent / "fixtures"

# Saved real responses (October 2026), served by URL so tests run offline.
ROUTES = {
    ("api.crossref.org", "/works"): "crossref_nber.json",
    ("api.crossref.org", "/journals/0012-9682/works"): "crossref_econometrica.json",
    ("api.openalex.org", "/works"): "openalex_nber.json",
    ("www.ecb.europa.eu", "/rss/wppub.html"): "rss_ecb.xml",
    ("www.fedinprint.org", "/rss/newyork.rss"): "rss_fedinprint_ny.xml",
    ("www.bankofengland.co.uk", "/rss/publications"): "rss_boe.xml",
}


def fixture_handler(request: httpx.Request) -> httpx.Response:
    name = ROUTES.get((request.url.host, request.url.path))
    if name is None:
        return httpx.Response(404)
    return httpx.Response(200, content=(FIXTURES / name).read_bytes())


@pytest.fixture
def http() -> HttpClient:
    return HttpClient("test@example.org", min_interval=0, transport=httpx.MockTransport(fixture_handler))


@pytest.fixture
def conn(tmp_path):
    connection = db.connect(tmp_path / "test.db")
    yield connection
    connection.close()
