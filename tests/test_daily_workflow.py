"""Tests for Stage 4 daily workflow helpers.

These tests cover pure / near-pure functions extracted from app/bot/main.py:
  - _build_fast_payload: snippet-only payload builder
  - _format_daily_card: compact Telegram card formatter
  - filtering / sorting logic (tested via direct logic, no Telegram mocks)
  - DAILY_TOP_N constant
  - search profile integration
"""

from __future__ import annotations

from app.bot.main import (
    DAILY_TOP_N,
    _build_fast_payload,
    _format_daily_card,
)
from app.config.search_profiles import DEFAULT_PROFILE_NAME, get_profile
from app.scoring.engine import ScoringEngine, ScoringResult
from app.services.vacancy import Vacancy

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _make_vacancy(
    vacancy_id: str = "12345",
    name: str = "Python AI Developer",
    employer: str = "Tech Corp",
    url: str = "https://hh.ru/vacancy/12345",
    snippet: str = "Требования: Python, FastAPI",
    responsibility: str = "Разработка AI автоматизации",
) -> Vacancy:
    return Vacancy(
        id=vacancy_id,
        name=name,
        employer=employer,
        url=url,
        snippet_requirement=snippet,
        snippet_responsibility=responsibility,
    )


def _make_result(
    total_score: int = 75,
    strengths: list | None = None,
    risks: list | None = None,
    is_remote: bool = True,
) -> ScoringResult:
    return ScoringResult(
        total_score=total_score,
        role_fit=20,
        task_fit=25,
        stack_fit=10,
        growth_fit=5,
        risk_penalty=0,
        strengths=strengths or ["Python Automation", "AI Agent"],
        risks=risks or [],
        recommendation="Хороший матч.",
        is_remote=is_remote,
    )


# ---------------------------------------------------------------------------
# _build_fast_payload
# ---------------------------------------------------------------------------


def test_fast_payload_returns_dict():
    v = _make_vacancy()
    payload = _build_fast_payload(v)
    assert isinstance(payload, dict)


def test_fast_payload_includes_vacancy_name():
    v = _make_vacancy(name="Senior LLM Engineer")
    payload = _build_fast_payload(v)
    assert payload.get("name") == "Senior LLM Engineer"


def test_fast_payload_includes_snippet():
    v = _make_vacancy(snippet="Python FastAPI OpenAI")
    payload = _build_fast_payload(v)
    assert payload.get("snippet_requirement") == "Python FastAPI OpenAI"


def test_fast_payload_has_no_separate_api_fetch():
    # model_dump() should NOT have a non-empty "description" field from HH
    # (it will be None or absent, never fetched via API)
    v = _make_vacancy()
    payload = _build_fast_payload(v)
    # description key may be absent or None — it's not fetched from HH API
    assert not payload.get("description"), (
        "_build_fast_payload must not fetch full description from HH API"
    )


def test_fast_payload_is_scorable():
    """Ensure the payload can be passed to ScoringEngine without error."""
    v = _make_vacancy()
    payload = _build_fast_payload(v)
    scorer = ScoringEngine()
    result = scorer.score_detailed(payload)
    assert isinstance(result, ScoringResult)
    assert 0 <= result.total_score <= 100


# ---------------------------------------------------------------------------
# _format_daily_card
# ---------------------------------------------------------------------------


def test_daily_card_starts_with_rank_and_name():
    v = _make_vacancy(name="AI Automation Engineer")
    result = _make_result()
    card = _format_daily_card(1, v, result)
    assert card.startswith("#1 ") or "<b>#1 " in card


def test_daily_card_contains_score():
    v = _make_vacancy()
    result = _make_result(total_score=82)
    card = _format_daily_card(1, v, result)
    assert "82" in card


def test_daily_card_contains_company():
    v = _make_vacancy(employer="Yandex")
    result = _make_result()
    card = _format_daily_card(1, v, result)
    assert "Yandex" in card


def test_daily_card_contains_strengths():
    v = _make_vacancy()
    result = _make_result(strengths=["FastAPI", "AI automation"])
    card = _format_daily_card(1, v, result)
    assert "+ FastAPI" in card


def test_daily_card_shows_at_most_two_strengths():
    v = _make_vacancy()
    result = _make_result(strengths=["A", "B", "C", "D"])
    card = _format_daily_card(1, v, result)
    assert card.count("+ ") <= 2


def test_daily_card_shows_at_most_one_risk():
    v = _make_vacancy()
    result = _make_result(risks=["офис", "Java", "1С"])
    card = _format_daily_card(1, v, result)
    assert card.count("- ") <= 1


def test_daily_card_contains_url():
    v = _make_vacancy(url="https://hh.ru/vacancy/99999")
    result = _make_result()
    card = _format_daily_card(2, v, result)
    assert "https://hh.ru/vacancy/99999" in card


def test_daily_card_office_warning():
    v = _make_vacancy()
    result = _make_result(is_remote=False)
    card = _format_daily_card(1, v, result)
    assert "офис" in card.lower()


def test_daily_card_rank_number():
    v = _make_vacancy(name="Role X")
    result = _make_result()
    card_3 = _format_daily_card(3, v, result)
    assert "#3" in card_3


# ---------------------------------------------------------------------------
# DAILY_TOP_N constant
# ---------------------------------------------------------------------------


def test_daily_top_n_is_positive():
    assert DAILY_TOP_N > 0


def test_daily_top_n_default_value():
    assert DAILY_TOP_N == 5


# ---------------------------------------------------------------------------
# Sorting and filtering logic (pure, no Telegram)
# ---------------------------------------------------------------------------


def test_top_n_selection_returns_highest_scores():
    """Simulate the sorting/top-N logic from cmd_daily."""
    vacancies = [
        _make_vacancy(vacancy_id=str(i), name=f"Role {i}")
        for i in range(10)
    ]
    scored: list[tuple[Vacancy, ScoringResult]] = []
    for i, v in enumerate(vacancies):
        # Manually assign distinct scores by overriding total_score
        result = _make_result(total_score=i * 8)  # 0, 8, 16, ..., 72
        scored.append((v, result))

    scored.sort(key=lambda x: x[1].total_score, reverse=True)
    top = scored[:DAILY_TOP_N]

    assert len(top) == DAILY_TOP_N
    scores = [r.total_score for _, r in top]
    # First element must be highest score
    assert scores[0] == max(r.total_score for _, r in scored)
    # Scores must be in descending order
    assert scores == sorted(scores, reverse=True)


def test_dedup_excludes_already_seen():
    """Simulate the filtering logic: skip vacancies in st['seen']."""
    seen: set[str] = {"11111", "22222"}
    vacancies = [
        _make_vacancy(vacancy_id="11111"),  # already seen
        _make_vacancy(vacancy_id="33333"),  # new
        _make_vacancy(vacancy_id="22222"),  # already seen
    ]
    candidates = [v for v in vacancies if v.id not in seen]
    assert len(candidates) == 1
    assert candidates[0].id == "33333"


def test_top_n_limit_respected():
    """Simulate top-N selection with more candidates than DAILY_TOP_N."""
    candidates = [_make_vacancy(vacancy_id=str(i)) for i in range(20)]
    scored = [(v, _make_result(total_score=i)) for i, v in enumerate(candidates)]
    scored.sort(key=lambda x: x[1].total_score, reverse=True)
    top = scored[:DAILY_TOP_N]
    assert len(top) == DAILY_TOP_N


def test_empty_candidates_list():
    """When all candidates are filtered, top is empty — no crash."""
    scored: list[tuple[Vacancy, ScoringResult]] = []
    scored.sort(key=lambda x: x[1].total_score, reverse=True)
    top = scored[:DAILY_TOP_N]
    assert top == []


# ---------------------------------------------------------------------------
# Profile integration
# ---------------------------------------------------------------------------


def test_active_profile_default_is_ai_builder():
    from app.bot.main import _new_state

    st = _new_state()
    assert st["active_profile"] == DEFAULT_PROFILE_NAME


def test_vacancy_cache_starts_empty():
    from app.bot.main import _new_state

    st = _new_state()
    assert st["vacancy_cache"] == {}


def test_profile_query_forwarded():
    """Verify each profile has a non-empty query (forwarded to HH API)."""
    for name in ["ai_builder", "llm_engineer", "fastapi_backend"]:
        profile = get_profile(name)
        assert profile is not None
        assert len(profile.query.strip()) > 0
