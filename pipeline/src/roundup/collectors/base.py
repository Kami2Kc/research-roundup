"""Shared HTTP behaviour for every collector, plus small text helpers."""

import html
import logging
import re
import time
import urllib.robotparser
from urllib.parse import urlsplit

import httpx

log = logging.getLogger(__name__)

RETRY_STATUSES = {429, 500, 502, 503, 504}
TAG_RE = re.compile(r"<[^>]+>")


class RobotsDisallowed(Exception):
    pass


class HttpClient:
    """A polite HTTP client.

    - descriptive User-Agent with a contact email
    - timeouts, and retries with exponential backoff on network errors, 429 and 5xx
    - at most one request per `min_interval` seconds per host (or the robots.txt crawl delay, if longer)
    - robots.txt is checked before every request
    """

    def __init__(self, contact_email: str, *, min_interval: float = 1.0, max_retries: int = 3,
                 transport: httpx.BaseTransport | None = None):
        self.contact_email = contact_email
        self.user_agent = (
            "ResearchRoundup/0.1 (+https://github.com/Kami2Kc/research-roundup; "
            f"mailto:{contact_email})"
        )
        self.min_interval = min_interval
        self.max_retries = max_retries
        self._client = httpx.Client(
            headers={"User-Agent": self.user_agent}, timeout=30, follow_redirects=True, transport=transport
        )
        self._last_request: dict[str, float] = {}
        self._robots: dict[str, urllib.robotparser.RobotFileParser] = {}

    def get(self, url: str, params: dict | None = None) -> httpx.Response:
        if not self._allowed(url):
            raise RobotsDisallowed(f"robots.txt disallows {url}")
        host = urlsplit(url).netloc
        for attempt in range(self.max_retries + 1):
            self._wait_turn(host)
            try:
                response = self._client.get(url, params=params)
            except httpx.TransportError as e:
                if attempt == self.max_retries:
                    raise
                log.warning("%s: %s (attempt %d)", url, type(e).__name__, attempt + 1)
            else:
                if response.status_code not in RETRY_STATUSES or attempt == self.max_retries:
                    response.raise_for_status()
                    return response
                log.warning("%s: HTTP %d (attempt %d)", url, response.status_code, attempt + 1)
                retry_after = response.headers.get("retry-after", "")
                if retry_after.isdigit():
                    time.sleep(min(int(retry_after), 60))
                    continue
            time.sleep(2**attempt)
        raise AssertionError("unreachable")

    def _wait_turn(self, host: str) -> None:
        interval = max(self.min_interval, self._crawl_delay(host))
        elapsed = time.monotonic() - self._last_request.get(host, 0.0)
        if elapsed < interval:
            time.sleep(interval - elapsed)
        self._last_request[host] = time.monotonic()

    def _robots_for(self, url: str) -> urllib.robotparser.RobotFileParser:
        parts = urlsplit(url)
        base = f"{parts.scheme}://{parts.netloc}"
        if base not in self._robots:
            parser = urllib.robotparser.RobotFileParser()
            try:
                self._wait_turn(parts.netloc)
                r = self._client.get(base + "/robots.txt")
                if r.status_code == 200:
                    parser.parse(r.text.splitlines())
                elif r.status_code in (401, 403):
                    parser.disallow_all = True
                else:
                    parser.allow_all = True
            except httpx.TransportError:
                parser.allow_all = True
            self._robots[base] = parser
        return self._robots[base]

    def _allowed(self, url: str) -> bool:
        return self._robots_for(url).can_fetch(self.user_agent, url)

    def _crawl_delay(self, host: str) -> float:
        for base, parser in self._robots.items():
            if urlsplit(base).netloc == host:
                return float(parser.crawl_delay(self.user_agent) or 0)
        return 0.0


def clean_text(value: str | None) -> str:
    """Strip HTML/JATS tags and entities, and collapse whitespace."""
    if not value:
        return ""
    text = html.unescape(TAG_RE.sub(" ", value))
    return " ".join(text.split())
