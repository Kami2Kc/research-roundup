"""Weekly screening: score each new paper's relevance and classify its market focus (EM / DM / Transversal)."""

import hashlib
import logging
import sqlite3
from dataclasses import dataclass
from datetime import date
from typing import Literal

from pydantic import BaseModel, Field, field_validator

from roundup import db
from roundup.llm import LLM, LLMError, estimate_cost
from roundup.models import Source

log = logging.getLogger(__name__)

# v2: euro area periphery is DM; non-euro CEE and the Gulf are EM
# v3: fixed topic list, region naming rules, sector and methods guidance, calibration examples
PROMPT_VERSION = "screen-v3"
MIN_ABSTRACT_CHARS = 100  # shorter "abstracts" are feed teasers, too thin to classify
FOCUSES = ("EM", "DM", "Transversal")

# A fixed list so the dashboard can filter by topic.
Topic = Literal[
    "monetary policy", "inflation", "interest rates and bonds", "fx and capital flows",
    "credit and corporate finance", "banking and financial stability", "fiscal policy and sovereign debt",
    "growth and productivity", "labour markets", "trade and supply chains", "housing and real estate",
    "energy and commodities", "climate and esg", "equities and asset pricing", "households and consumption",
    "payments and digital money", "ai and technology", "industrials, autos and retail", "development",
    "econometrics and forecasting", "health, education and social policy", "other",
]


class ScreeningResult(BaseModel):
    relevance_score: int = Field(ge=0, le=10)
    market_focus: Literal["EM", "DM", "Transversal"]
    focus_rationale: str
    topics: list[Topic] = Field(min_length=1, max_length=3)
    regions: list[str]

    # The JSON schema can't forbid repeats, and the model occasionally lists a topic twice.
    @field_validator("topics", "regions")
    @classmethod
    def drop_duplicates(cls, values: list[str]) -> list[str]:
        return list(dict.fromkeys(values))


SYSTEM_PROMPT = """\
You screen new economics research for the Global Markets Research team of a European corporate and \
investment bank. The team covers rates, FX, credit, macro and emerging markets, plus sector research on \
industrials, autos, retail and ESG. Its readers are sell-side strategists and economists who want research \
that changes how they think about markets, policy or the economic outlook.

You get each paper's title, source and abstract (never the full text). Return:

relevance_score: an integer from 0 to 10 for how useful the paper is to this team.
- 9-10: directly about market pricing, monetary or fiscal policy and its transmission, inflation, interest \
rates, FX, credit, sovereign risk, capital flows or financial stability, with implications a strategist \
could use now.
- 6-8: a macro or financial topic with a clear indirect link to markets: labour markets, productivity, \
trade, housing, banking, energy, equities, the climate transition, or dynamics in industrials, autos or \
retail. Forecasting and nowcasting methods that macro economists can apply belong here too.
- 3-5: economics with a weak link to markets, such as most applied microeconomics, public-finance details, \
general econometric theory, or development topics without a macro or financial angle.
- 0-2: no meaningful link: health, education, history, pure theory with no application, or items that are \
not research.
Calibration examples:
- "Treasury issuance and dealer balance sheets" (repo and bond market functioning): 9.
- "Monetary policy transmission in Morocco after an exchange-rate reform": 8.
- "Pricing power in the US mortgage market": 7.
- "Clustered standard errors for regression with spatial data": 3.
- "Selective admissions in nursing homes": 2.

market_focus: exactly one of "EM", "DM" or "Transversal".
- DM: mainly about advanced economies, such as the US, the euro area, the UK, Japan, Canada, Switzerland, \
the Nordics, Australia and New Zealand. Every euro area member is DM, including the periphery (Italy, Spain, \
Portugal, Greece, Ireland). A study of several advanced economies is still DM.
- EM: mainly about emerging or developing economies, such as China, India, Brazil, Mexico, Turkey, South \
Africa, the Gulf states, and Central and Eastern European economies outside the euro area (such as Poland, \
Czechia, Hungary and Romania).
- Transversal: covers both groups, or is global, cross-country, theoretical or methodological with no \
particular focus on either.
Decide from the economies the paper studies, not from the institution that published it: an ECB paper \
about Chinese exports is EM, and a Federal Reserve paper with a purely theoretical model is Transversal.

focus_rationale: one or two sentences naming the economies studied, or why the paper is Transversal.
topics: one to three topics from the allowed list, most important first.
regions: the economies or regions studied, using short common names: "US", "euro area", "UK", "Japan", \
"China", "Germany", "Brazil", "Latin America", "sub-Saharan Africa". Use "global" for worldwide or broad \
cross-country samples. Use an empty list for theory with no particular place.
"""


def build_prompt(row: sqlite3.Row, source: Source | None) -> str:
    return (
        f"Title: {row['title']}\n"
        f"Source: {source.name if source else row['source_id']}\n"
        f"Abstract: {row['abstract']}"
    )


@dataclass
class ScreeningStats:
    screened: int = 0
    no_abstract: int = 0
    errors: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    cost_usd: float = 0.0


def screen_papers(conn: sqlite3.Connection, llm: LLM, model: str, sources: dict[str, Source],
                  limit: int, since: date | None = None, until: date | None = None) -> ScreeningStats:
    """Screen unscreened papers, newest first, making at most `limit` LLM calls. Screened papers are never redone.

    `since`/`until` restrict screening to papers published in that period (used by backfills).
    """
    stats = ScreeningStats()
    for row in db.papers_to_screen(conn):
        published = row["published_date"]
        if (since or until) and published is None:
            continue
        if (since and published < since.isoformat()) or (until and published > until.isoformat()):
            continue
        abstract = row["abstract"] or ""
        if len(abstract) < MIN_ABSTRACT_CHARS:
            reason = f"abstract too short ({len(abstract)} chars)" if abstract else "no abstract"
            db.save_screening(conn, row["id"], "no_abstract", error=reason)
            log.info("Skipped (%s): %s [%s]", reason, row["title"][:80], row["source_id"])
            stats.no_abstract += 1
            continue
        if stats.screened + stats.errors >= limit:
            continue  # keep marking papers without abstracts, but make no more LLM calls

        try:
            result = llm.complete_json(
                ScreeningResult, build_prompt(row, sources.get(row["source_id"])), model,
                system=SYSTEM_PROMPT, max_tokens=2000, effort="low",
            )
        except LLMError as e:
            db.save_screening(conn, row["id"], "error", model=model, prompt_version=PROMPT_VERSION, error=str(e))
            log.warning("Screening failed for %s: %s", row["id"], e)
            stats.errors += 1
            continue

        db.save_screening(
            conn, row["id"], "screened", result=result.data.model_dump(), model=result.model,
            prompt_version=PROMPT_VERSION, input_tokens=result.input_tokens, output_tokens=result.output_tokens,
        )
        stats.screened += 1
        stats.input_tokens += result.input_tokens
        stats.output_tokens += result.output_tokens
        stats.cost_usd += estimate_cost(result.model, result.input_tokens, result.output_tokens) or 0.0
    return stats


def fake_screening(prompt: str) -> ScreeningResult:
    """Deterministic, offline classification used by FakeLLM."""
    h = int(hashlib.md5(prompt.encode()).hexdigest(), 16)
    return ScreeningResult(
        relevance_score=h % 11,
        market_focus=("EM", "DM", "Transversal")[h % 3],
        focus_rationale="Placeholder classification from FakeLLM.",
        topics=["other"],
        regions=[],
    )


FAKE_RESPONDERS = {ScreeningResult: fake_screening}
