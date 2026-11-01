import pytest

from roundup import db
from roundup.llm import FakeLLM, LLMError
from roundup.screening import PROMPT_VERSION, ScreeningResult, fake_screening, screen_papers
from tests.test_db import make_paper

ABSTRACT = "We study how monetary policy shocks transmit to sovereign bond yields across the euro area. " * 2
VALID = ('{"relevance_score": 8, "market_focus": "DM", "focus_rationale": "Euro area.", '
         '"topics": ["interest rates and bonds"], "regions": ["euro area"]}')


def responder_from(outputs: list[str]):
    queue = list(outputs)
    return FakeLLM({ScreeningResult: lambda prompt: queue.pop(0)})


def test_invalid_output_is_retried_then_accepted():
    llm = responder_from(['{"relevance_score": 14}', "not json", VALID])
    result = llm.complete_json(ScreeningResult, "prompt", "fake")
    assert result.data.relevance_score == 8
    assert len(llm.calls) == 3


def test_invalid_output_three_times_raises():
    llm = responder_from(['{"market_focus": "Frontier"}'] * 3)
    with pytest.raises(LLMError):
        llm.complete_json(ScreeningResult, "prompt", "fake")


def test_out_of_range_score_is_rejected():
    with pytest.raises(ValueError):
        ScreeningResult.model_validate_json(VALID.replace("8", "11"))


def test_topics_must_come_from_the_fixed_list():
    with pytest.raises(ValueError):
        ScreeningResult.model_validate_json(VALID.replace("interest rates and bonds", "rates"))


def test_repeated_topics_and_regions_are_dropped():
    output = VALID.replace('["interest rates and bonds"]', '["interest rates and bonds", "fiscal policy and sovereign debt", "interest rates and bonds"]')
    result = ScreeningResult.model_validate_json(output.replace('["euro area"]', '["euro area", "euro area"]'))
    assert result.topics == ["interest rates and bonds", "fiscal policy and sovereign debt"]
    assert result.regions == ["euro area"]


def test_screening_skips_missing_abstracts_and_never_rescreens(conn):
    db.upsert_papers(conn, [make_paper(id="10.1/a", abstract=ABSTRACT), make_paper(id="10.1/b", abstract=None),
                            make_paper(id="10.1/c", abstract="Too short.")])
    llm = FakeLLM({ScreeningResult: fake_screening})

    stats = screen_papers(conn, llm, "fake", {}, limit=10)
    assert (stats.screened, stats.no_abstract) == (1, 2)
    row = conn.execute("SELECT * FROM screenings WHERE paper_id = '10.1/a'").fetchone()
    assert row["status"] == "screened" and row["prompt_version"] == PROMPT_VERSION

    db.save_screening(conn, "10.1/a", "screened", model="claude-haiku-5-5", prompt_version=PROMPT_VERSION)
    stats = screen_papers(conn, llm, "fake", {}, limit=10)
    assert stats.screened == 0 and len(llm.calls) == 1  # a real screening is never sent again


def test_placeholder_screenings_from_fakellm_are_redone(conn):
    db.upsert_papers(conn, [make_paper(abstract=ABSTRACT)])
    llm = FakeLLM({ScreeningResult: fake_screening})
    screen_papers(conn, llm, "fake", {}, limit=10)
    screen_papers(conn, llm, "fake", {}, limit=10)
    assert len(llm.calls) == 2


def test_screening_respects_the_limit(conn):
    db.upsert_papers(conn, [make_paper(id=f"10.1/{i}", abstract=ABSTRACT) for i in range(5)])
    llm = FakeLLM({ScreeningResult: fake_screening})
    assert screen_papers(conn, llm, "fake", {}, limit=2).screened == 2
    assert len(llm.calls) == 2


def test_failed_screening_is_stored_as_error_and_retried_later(conn):
    db.upsert_papers(conn, [make_paper(abstract=ABSTRACT)])
    stats = screen_papers(conn, responder_from(["bad"] * 3), "fake", {}, limit=10)
    assert stats.errors == 1
    assert conn.execute("SELECT status FROM screenings").fetchone()[0] == "error"
    assert screen_papers(conn, responder_from([VALID]), "fake", {}, limit=10).screened == 1
