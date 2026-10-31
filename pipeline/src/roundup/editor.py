"""Monthly editor: choose 5-8 papers from the month's pool, justify the choice, and write each one up.

This is the agentic step. The model reviews the whole pool and explains its selection; the code checks the
selection against the rules (count, valid IDs, market-focus balance) and sends any problems back for a revision.
"""

import json
import logging
import re
import sqlite3
from dataclasses import dataclass
from typing import Callable, Literal, TypeVar

from pydantic import BaseModel, Field

from roundup import db
from roundup.llm import LLM, LLMError, LLMResult
from roundup.models import Source

log = logging.getLogger(__name__)

PROMPT_VERSION = "editor-v1"
POOL_CAP = 40  # the highest-scored candidates go to the editor
MIN_PICKS, MAX_PICKS = 5, 8
REVISIONS = 2
FOCUSES = ("EM", "DM", "Transversal")

T = TypeVar("T", bound=BaseModel)


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


SELECT_SYSTEM = """\
You are the editor of The Research Roundup, a monthly newsletter that brings the month's most useful new \
economics research to the Global Markets Research team of a European corporate and investment bank. The team \
covers rates, FX, credit, macro and emerging markets, plus sector research on industrials, autos, retail and ESG.

You receive the month's candidate papers. Each has been screened already: it has a relevance score out of 10 \
and a market focus (EM, DM or Transversal). Choose the papers for this month's issue:
- Choose between 5 and 8 papers.
- Prefer higher relevance. A lower-scored paper should beat a higher-scored one only when it adds something \
the issue would otherwise lack.
- Balance market focus: where the pool allows, include at least one EM, one DM and one Transversal paper.
- Avoid near-duplicates: no two papers on essentially the same question.
- When quality is similar, prefer a spread of sources (journals, central banks, international organisations).

Order the picks from most to least important and give a one-sentence reason for each. Then write a rationale \
of three to five sentences for the issue as a whole: what you prioritised, and what notable candidates you left \
out and why.
"""

WRITE_SYSTEM = """\
You write The Research Roundup, a monthly newsletter of new economics research for the Global Markets Research \
team of a European corporate and investment bank (rates, FX, credit, macro, emerging markets, sectors).

For each paper you receive its metadata, abstract and screening classification. You never see the full text, \
so base everything on the abstract: never invent data, numbers, methods or findings that it does not state.

For each paper, write:
- headline: a plain, specific headline of at most 12 words. No hype, no puns.
- summary: about 120 words in plain language: the question, how the authors answer it, and what they find.
- takeaways: exactly three key takeaways, one sentence each.
- why_it_matters: two or three sentences on what the paper means for views on rates, FX, credit, macro or \
emerging markets. Be concrete but do not overclaim.
- market_focus: keep the screening classification unless it is clearly wrong.
- focus_rationale: one sentence for readers explaining the market focus.

Then write editor_note: 80 to 120 words introducing the issue, its main themes, and how the papers connect.

Use British English and plain text (no markdown).
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
    return conn.execute(
        """SELECT p.*, s.relevance_score, s.market_focus, s.focus_rationale, s.topics, s.regions
           FROM papers p JOIN screenings s ON s.paper_id = p.id
           WHERE s.status = 'screened' AND substr(p.published_date, 1, 7) = ? AND s.relevance_score >= ?
           ORDER BY s.relevance_score DESC, p.published_date DESC LIMIT ?""",
        (month, threshold, POOL_CAP),
    ).fetchall()


def format_candidate(row: sqlite3.Row, source: Source | None, heading: str = "Candidate") -> str:
    return (
        f"### {heading} [{row['id']}]\n"
        f"Title: {row['title']}\n"
        f"Source: {source.name if source else row['source_id']}\n"
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
    raise LLMError(f"{schema.__name__} still invalid after {1 + REVISIONS} attempts")


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
    available = {row["market_focus"] for row in pool}
    chosen = {by_id[i]["market_focus"] for i in ids if i in by_id}
    if missing := [f for f in FOCUSES if f in available and f not in chosen]:
        problems.append(f"The pool has {', '.join(missing)} papers but none were chosen; include at least one of each.")
    return problems


def check_draft(draft: IssueDraft, picked_ids: list[str]) -> list[str]:
    written = [w.paper_id for w in draft.papers]
    if sorted(written) != sorted(picked_ids):
        return [f"Write up exactly these papers, once each: {', '.join(picked_ids)}."]
    return []


def build_issue(conn: sqlite3.Connection, llm: LLM, model: str, month: str, sources: dict[str, Source],
                threshold: int) -> BuiltIssue:
    pool = candidate_pool(conn, month, threshold)
    if not pool:
        raise LLMError(f"No screened papers for {month} with relevance >= {threshold}")
    papers_screened = conn.execute(
        """SELECT COUNT(*) FROM papers p JOIN screenings s ON s.paper_id = p.id
           WHERE s.status = 'screened' AND substr(p.published_date, 1, 7) = ?""",
        (month,),
    ).fetchone()[0]

    candidates = "\n".join(format_candidate(row, sources.get(row["source_id"])) for row in pool)
    selection = ask_until_valid(
        llm, Selection, f"Issue month: {month}\n\n{len(pool)} candidates:\n\n{candidates}", model, SELECT_SYSTEM,
        lambda s: check_selection(s, pool),
    )
    picked_ids = [p.paper_id for p in selection.data.picks]
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
        papers.append({**dict(row), **w.model_dump(), "screening_focus": row["market_focus"],
                       "selection_reason": reasons[i], "authors": json.loads(row["authors"]),
                       "source_name": sources[row["source_id"]].name})

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
CANDIDATE_RE = re.compile(r"### (?:Candidate|Paper) \[(.+?)\]\nTitle: (.*)\n(?:.*\n){2}Market focus: (\w+)")


def fake_selection(prompt: str) -> Selection:
    candidates = CANDIDATE_RE.findall(prompt)
    picks, seen_focus = [], set()
    for paper_id, _, focus in candidates:  # one of each focus first, then fill up
        if focus not in seen_focus:
            picks.append(paper_id)
            seen_focus.add(focus)
    picks += [c[0] for c in candidates if c[0] not in picks][: max(0, 6 - len(picks))]
    return Selection(picks=[Pick(paper_id=i, reason="Placeholder reason from FakeLLM.") for i in picks],
                     rationale="Placeholder rationale from FakeLLM.")


def fake_draft(prompt: str) -> IssueDraft:
    return IssueDraft(
        editor_note="Placeholder editor's note from FakeLLM.",
        papers=[
            Writeup(paper_id=paper_id, headline=title[:80], summary="Placeholder summary from FakeLLM.",
                    takeaways=["Placeholder takeaway one.", "Placeholder takeaway two.", "Placeholder takeaway three."],
                    why_it_matters="Placeholder relevance note from FakeLLM.", market_focus=focus,
                    focus_rationale="Placeholder focus rationale from FakeLLM.")
            for paper_id, title, focus in CANDIDATE_RE.findall(prompt)
        ],
    )


FAKE_RESPONDERS = {Selection: fake_selection, IssueDraft: fake_draft}
