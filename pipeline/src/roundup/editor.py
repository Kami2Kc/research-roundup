"""Monthly editor: choose 5-8 papers from the month's pool, justify the choice, and write each one up.

This is the agentic step. The model reviews the whole pool and explains its selection; the code checks the
selection and the write-ups against the house rules (count, balance, variety, length) and sends any problems
back to the model for a revision, up to twice.
"""

import json
import logging
import re
import sqlite3
from collections import Counter
from dataclasses import dataclass
from typing import Callable, Literal, TypeVar

from pydantic import BaseModel, Field

from roundup import db
from roundup.llm import LLM, LLMError, LLMResult
from roundup.models import Source
from roundup.screening import FOCUSES

log = logging.getLogger(__name__)

# v2: balanced candidate pool; checks for focus balance, source and topic variety, and write-up length
PROMPT_VERSION = "editor-v2"
POOL_CAP = 40  # candidates shown to the editor
MIN_PER_FOCUS = 8  # pool places reserved for each market focus, so a DM-heavy month still offers EM papers
MIN_POOL_ABSTRACT_CHARS = 400  # a thinner abstract can't support a 120-word summary without padding
MIN_PICKS, MAX_PICKS = 5, 8
MAX_PER_SOURCE = 2
MAX_PER_TOPIC = 2  # papers sharing the same main topic
REVISIONS = 2
WORD_LIMITS = {"headline": (4, 14), "summary": (80, 170), "why_it_matters": (25, 90), "editor_note": (60, 160)}

SOURCE_TYPES = {
    "journal": "Academic journal", "nber": "NBER working paper", "bpea": "Brookings Papers",
    "intl_org": "International organisation", "g10_cb": "G10 central bank",
    "fed_regional": "Regional Federal Reserve Bank", "european_ncb": "European central bank",
}

T = TypeVar("T", bound=BaseModel)


class EmptyPoolError(LLMError):
    """No screened papers qualify for the month, so there is nothing to edit."""


class Pick(BaseModel):
    paper_id: str
    reason: str


class Selection(BaseModel):
    picks: list[Pick]
    rationale: str


class Writeup(BaseModel):
    paper_id: str
    headline: str
    summary: str
    takeaways: list[str] = Field(min_length=3, max_length=3)
    why_it_matters: str
    market_focus: Literal["EM", "DM", "Transversal"]
    focus_rationale: str


class IssueDraft(BaseModel):
    editor_note: str
    papers: list[Writeup]


SELECT_SYSTEM = f"""\
You are the editor of The Research Roundup, a monthly newsletter that brings the month's most useful new \
economics research to the Global Markets Research team of a European corporate and investment bank. The team \
covers rates, FX, credit, macro and emerging markets, plus sector research on industrials, autos, retail and ESG.

You receive the month's candidate papers. Each has been screened already: it has a relevance score out of 10, \
a market focus (EM, DM or Transversal) and topics. The pool deliberately includes the best EM and Transversal \
papers even when they score lower than the DM papers. Choose the papers for this month's issue:
- Choose between {MIN_PICKS} and {MAX_PICKS} papers.
- Prefer higher relevance. A lower-scored paper should beat a higher-scored one only when it adds something \
the issue would otherwise lack.
- Balance market focus: include at least one EM, one DM and one Transversal paper where the pool has them, \
and no more than half the issue from any one focus.
- Variety: at most {MAX_PER_SOURCE} papers from the same source, and at most {MAX_PER_TOPIC} papers whose main \
(first-listed) topic is the same. Never pick two papers on essentially the same question.
- When quality is similar, prefer a mix of source types (journals, central banks, international organisations).

Order the picks from most to least important and give a one-sentence reason for each. Then write a rationale \
of three to five sentences for the issue as a whole: what you prioritised, and which notable candidates you \
left out and why.
"""

WRITE_SYSTEM = """\
You write The Research Roundup, a monthly newsletter of new economics research for the Global Markets Research \
team of a European corporate and investment bank (rates, FX, credit, macro, emerging markets, sectors). Readers \
are busy strategists and economists: write so they can grasp each paper in under a minute.

For each paper you receive its metadata, abstract and screening classification. You never see the full text, \
so base everything on the abstract: never invent data, numbers, methods or findings that it does not state, \
and keep any figures exactly as the abstract gives them.

For each paper, write:
- headline: a plain, specific headline of at most 12 words that states the finding. No hype, no puns, no \
question marks.
- summary: about 120 words (between 90 and 150) in plain language: the question, how the authors answer it, and \
what they find. Spell out acronyms on first use (except US, UK, GDP, ECB, IMF).
- takeaways: exactly three key takeaways, one sentence of at most 25 words each, none repeating the headline.
- why_it_matters: two or three sentences (40 to 80 words) on what the paper means for views on rates, FX, \
credit, macro, emerging markets or the sectors the team covers. Be concrete about the channel or asset class, \
but do not overclaim or give investment advice.
- market_focus: keep the screening classification unless it is clearly wrong.
- focus_rationale: one sentence for readers explaining the market focus.

Then write editor_note: 80 to 130 words introducing the issue: the month's main themes and how the papers \
connect. Do not list every paper.

Use British English and plain text (no markdown, no bullet characters).
"""


@dataclass
class BuiltIssue:
    month: str
    editor_note: str
    selection_rationale: str
    papers: list[dict]  # paper metadata merged with its write-up, in issue order
    pool_size: int
    papers_screened: int


def candidate_pool(conn: sqlite3.Connection, month: str, threshold: int) -> list[sqlite3.Row]:
    """The month's best papers above the threshold, reserving places for each market focus."""
    rows = conn.execute(
        """SELECT p.*, s.relevance_score, s.market_focus, s.focus_rationale, s.topics, s.regions
           FROM papers p JOIN screenings s ON s.paper_id = p.id
           WHERE s.status = 'screened' AND substr(p.published_date, 1, 7) = ? AND s.relevance_score >= ?
             AND length(p.abstract) >= ?
           ORDER BY s.relevance_score DESC, p.published_date DESC""",
        (month, threshold, MIN_POOL_ABSTRACT_CHARS),
    ).fetchall()
    reserved = [r for focus in FOCUSES for r in [r for r in rows if r["market_focus"] == focus][:MIN_PER_FOCUS]]
    reserved_ids = {r["id"] for r in reserved}
    rest = [r for r in rows if r["id"] not in reserved_ids][: max(0, POOL_CAP - len(reserved))]
    chosen = {r["id"] for r in reserved + rest}
    return [r for r in rows if r["id"] in chosen]  # keep relevance order


def main_topic(row: sqlite3.Row) -> str:
    topics = json.loads(row["topics"])
    return topics[0] if topics else "other"


def format_candidate(row: sqlite3.Row, source: Source | None, heading: str = "Candidate") -> str:
    source_line = f"{source.name} ({SOURCE_TYPES.get(str(source.group), source.group)})" if source else row["source_id"]
    return (
        f"### {heading} [{row['id']}]\n"
        f"Title: {row['title']}\n"
        f"Source: {source_line}\n"
        f"Published: {row['published_date']}\n"
        f"Market focus: {row['market_focus']} (relevance {row['relevance_score']}/10). {row['focus_rationale']}\n"
        f"Topics: {', '.join(json.loads(row['topics']))}\n"
        f"Abstract: {row['abstract']}\n"
    )


def ask_until_valid(llm: LLM, schema: type[T], prompt: str, model: str, system: str,
                    check: Callable[[T], list[str]]) -> LLMResult[T]:
    """Ask for structured output; if `check` finds problems, show the model its answer and the problems and ask again."""
    feedback = ""
    tokens_in = tokens_out = 0
    for attempt in range(1 + REVISIONS):
        result = llm.complete_json(schema, prompt + feedback, model, system=system, max_tokens=16000,
                                   effort="high", fallback=True)
        tokens_in += result.input_tokens
        tokens_out += result.output_tokens
        problems = check(result.data)
        if not problems:
            return LLMResult(result.data, result.model, tokens_in, tokens_out)
        log.info("%s needs revision (attempt %d): %s", schema.__name__, attempt + 1, "; ".join(problems))
        feedback = (
            f"\n\nYour previous answer was:\n{result.data.model_dump_json()}\n\n"
            "It has these problems:\n- " + "\n- ".join(problems) + "\nFix them and give your full answer again."
        )
    raise LLMError(f"{schema.__name__} still breaks the rules after {1 + REVISIONS} attempts")


def check_selection(selection: Selection, pool: list[sqlite3.Row]) -> list[str]:
    by_id = {row["id"]: row for row in pool}
    ids = [p.paper_id for p in selection.picks]
    low, high = min(MIN_PICKS, len(pool)), MAX_PICKS
    problems = []
    if not low <= len(ids) <= high:
        problems.append(f"Choose between {low} and {high} papers; you chose {len(ids)}.")
    if unknown := [i for i in ids if i not in by_id]:
        problems.append(f"These IDs are not in the candidate list: {', '.join(unknown)}.")
    if len(set(ids)) != len(ids):
        problems.append("Each paper may be chosen only once.")
    picked = [by_id[i] for i in dict.fromkeys(ids) if i in by_id]

    available = Counter(row["market_focus"] for row in pool)
    chosen = Counter(row["market_focus"] for row in picked)
    if missing := [f for f in FOCUSES if available[f] and not chosen[f]]:
        problems.append(f"The pool has {', '.join(missing)} papers but none were chosen; include at least one of each.")
    if all(available[f] >= 2 for f in FOCUSES):  # only insist on balance when the pool allows it
        for focus, n in chosen.items():
            if n > len(picked) // 2:
                problems.append(f"{n} of {len(picked)} papers are {focus}; no more than half may share a market focus.")
    # Variety limits apply only when the pool can meet them and still fill the minimum number of picks
    # (a thin month with papers from just two sources can't offer five papers at two per source).
    if satisfiable(Counter(row["source_id"] for row in pool), MAX_PER_SOURCE, low):
        for source_id, n in Counter(row["source_id"] for row in picked).items():
            if n > MAX_PER_SOURCE:
                problems.append(f"{n} papers come from {source_id}; at most {MAX_PER_SOURCE} may share a source.")
    if satisfiable(Counter(main_topic(row) for row in pool), MAX_PER_TOPIC, low, unlimited="other"):
        for topic, n in Counter(main_topic(row) for row in picked).items():
            if n > MAX_PER_TOPIC and topic != "other":
                problems.append(f"{n} papers have the main topic '{topic}'; at most {MAX_PER_TOPIC} may share one.")
    return problems


def satisfiable(counts: Counter, cap: int, needed: int, unlimited: str | None = None) -> bool:
    """Can `needed` papers be chosen with at most `cap` per group (the `unlimited` group has no cap)?"""
    return sum(n if group == unlimited else min(n, cap) for group, n in counts.items()) >= needed


def word_count(text: str) -> int:
    return len(re.findall(r"\b[\w'’-]+\b", text))


def check_draft(draft: IssueDraft, picked_ids: list[str]) -> list[str]:
    written = [w.paper_id for w in draft.papers]
    if sorted(written) != sorted(picked_ids):
        return [f"Write up exactly these papers, once each: {', '.join(picked_ids)}."]
    problems = []
    low, high = WORD_LIMITS["editor_note"]
    if not low <= word_count(draft.editor_note) <= high:
        problems.append(f"The editor's note has {word_count(draft.editor_note)} words; it should have {low}-{high}.")
    for w in draft.papers:
        for field_name in ("headline", "summary", "why_it_matters"):
            low, high = WORD_LIMITS[field_name]
            n = word_count(getattr(w, field_name))
            if not low <= n <= high:
                problems.append(f"{w.paper_id}: {field_name} has {n} words; it should have {low}-{high}.")
    return problems


def build_issue(conn: sqlite3.Connection, llm: LLM, model: str, month: str, sources: dict[str, Source],
                threshold: int) -> BuiltIssue:
    pool = candidate_pool(conn, month, threshold)
    if not pool:
        raise EmptyPoolError(f"no screened papers for {month} with relevance >= {threshold}")
    papers_screened = conn.execute(
        """SELECT COUNT(*) FROM papers p JOIN screenings s ON s.paper_id = p.id
           WHERE s.status = 'screened' AND substr(p.published_date, 1, 7) = ?""",
        (month,),
    ).fetchone()[0]
    mix = Counter(row["market_focus"] for row in pool)
    header = (f"Issue month: {month}. {papers_screened} papers were screened this month; the {len(pool)} candidates "
              f"below scored at least {threshold}/10 (EM {mix['EM']}, DM {mix['DM']}, Transversal {mix['Transversal']}).")

    candidates = "\n".join(format_candidate(row, sources.get(row["source_id"])) for row in pool)
    selection = ask_until_valid(
        llm, Selection, f"{header}\n\n{candidates}", model, SELECT_SYSTEM, lambda s: check_selection(s, pool),
    )
    picked_ids = list(dict.fromkeys(p.paper_id for p in selection.data.picks))
    by_id = {row["id"]: row for row in pool}
    chosen = "\n".join(format_candidate(by_id[i], sources.get(by_id[i]["source_id"]), "Paper") for i in picked_ids)
    draft = ask_until_valid(
        llm, IssueDraft, f"Issue month: {month}\n\nPapers, in issue order:\n\n{chosen}", model, WRITE_SYSTEM,
        lambda d: check_draft(d, picked_ids),
    )

    reasons = {p.paper_id: p.reason for p in selection.data.picks}
    writeups = {w.paper_id: w for w in draft.data.papers}
    papers = []
    for i in picked_ids:
        row, w = by_id[i], writeups[i]
        if w.market_focus != row["market_focus"]:
            log.info("Editor changed market focus of %s from %s to %s", i, row["market_focus"], w.market_focus)
        source = sources[row["source_id"]]
        papers.append({**dict(row), **w.model_dump(), "screening_focus": row["market_focus"],
                       "selection_reason": reasons[i], "authors": json.loads(row["authors"]),
                       "source_name": source.name, "source_group": str(source.group)})

    issue = BuiltIssue(month, draft.data.editor_note, selection.data.rationale, papers, len(pool), papers_screened)
    save_issue(conn, issue, selection.model,
               selection.input_tokens + draft.input_tokens, selection.output_tokens + draft.output_tokens)
    return issue


def save_issue(conn: sqlite3.Connection, issue: BuiltIssue, model: str, input_tokens: int, output_tokens: int) -> None:
    """Store the issue, replacing any earlier build for the same month."""
    conn.execute("DELETE FROM issue_papers WHERE month = ?", (issue.month,))
    conn.execute("DELETE FROM issues WHERE month = ?", (issue.month,))
    conn.execute(
        "INSERT INTO issues VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (issue.month, issue.editor_note, issue.selection_rationale, issue.pool_size, issue.papers_screened,
         model, PROMPT_VERSION, input_tokens, output_tokens, db.now_utc()),
    )
    for position, p in enumerate(issue.papers, start=1):
        conn.execute(
            "INSERT INTO issue_papers VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (issue.month, p["id"], position, p["selection_reason"], p["headline"], p["summary"],
             json.dumps(p["takeaways"]), p["why_it_matters"], p["market_focus"], p["focus_rationale"]),
        )
    conn.commit()


# ── FakeLLM responders: deterministic output built from the prompt, for offline runs ──────────────────
CANDIDATE_RE = re.compile(r"### (?:Candidate|Paper) \[(.+?)\]\nTitle: (.*)\nSource: (.*)\n.*\nMarket focus: (\w+)")
FILLER = "This placeholder text stands in for a summary written by the editor model during offline runs. " * 6


def fake_selection(prompt: str) -> Selection:
    """One paper of each focus first, then fill up to six within the per-source and balance limits, then without."""
    candidates = CANDIDATE_RE.findall(prompt)
    picks: list[str] = []
    per_source, per_focus = Counter(), Counter()
    for pass_number in (1, 2, 3):
        for paper_id, _, source, focus in candidates:
            if len(picks) == 6 or paper_id in picks:
                continue
            if pass_number < 3 and (per_source[source] >= MAX_PER_SOURCE or per_focus[focus] >= 3):
                continue
            if pass_number == 1 and per_focus[focus]:
                continue
            picks.append(paper_id)
            per_source[source] += 1
            per_focus[focus] += 1
    return Selection(picks=[Pick(paper_id=i, reason="Placeholder reason from FakeLLM.") for i in picks],
                     rationale="Placeholder rationale from FakeLLM.")


def fake_draft(prompt: str) -> IssueDraft:
    return IssueDraft(
        editor_note=FILLER[:600],
        papers=[
            Writeup(paper_id=paper_id, headline=" ".join(title.split()[:10]) or "Placeholder headline",
                    summary=FILLER[:700],
                    takeaways=["Placeholder takeaway one.", "Placeholder takeaway two.", "Placeholder takeaway three."],
                    why_it_matters=FILLER[:350], market_focus=focus,
                    focus_rationale="Placeholder focus rationale from FakeLLM.")
            for paper_id, title, _, focus in CANDIDATE_RE.findall(prompt)
        ],
    )


FAKE_RESPONDERS = {Selection: fake_selection, IssueDraft: fake_draft}
