"""Tests for the rule-based ScoringEngine (v2: AI automation focus)."""

from __future__ import annotations

from app.scoring.engine import ScoringEngine, normalize_text

# ---------------------------------------------------------------------------
# normalize_text
# ---------------------------------------------------------------------------


def test_normalize_text_lowercases_and_strips_html():
    assert normalize_text("<p>Hello WORLD</p>") == "hello world"


def test_normalize_text_replaces_yo_and_long_dashes():
    text = "Удалёнка — гибрид"
    assert "ё" not in normalize_text(text)
    assert "—" not in normalize_text(text)


def test_normalize_text_replaces_hyphens_with_space():
    # Compound terms with hyphens should match patterns like "no code".
    assert "no code" in normalize_text("no-code")
    assert "ai автоматизац" in normalize_text(
        "AI-автоматизация"
    )


# ---------------------------------------------------------------------------
# ScoringEngine - positive scenarios
# ---------------------------------------------------------------------------


WEBMASTERS_DESCRIPTION = (
    "WebMasters ищет специалиста по AI-автоматизациям. "
    "Будем создавать AI-агентов, ассистентов, чат-ботов, делать автоворонки "
    "и интеграции на Python с использованием OpenAI API, n8n и Make. "
    "Работа с нейросетями и no-code/low-code инструментами. "
    "Создание инструкций, гайдов, кейсов, базы знаний, контента и описаний "
    "продуктов. Пользовательские сценарии, продуктовые гипотезы, MVP. "
    "Удалённо. Развитие AI-направления и внутренних проектов команды."
)


def test_webmasters_like_vacancy_scores_high():
    """The exact scenario that previously scored 20/100 must now score 80+."""
    engine = ScoringEngine()
    score, reasons = engine.score(
        {
            "name": "Специалист по AI-автоматизациям",
            "employer": "WebMasters",
            "snippet_requirement": "AI-автоматизации, нейросети, no-code/low-code",
            "snippet_responsibility": "Создание AI-ботов, AI-агентов, контент и кейсы",
            "description": WEBMASTERS_DESCRIPTION,
            "schedule": "удалённо",
        }
    )
    assert score >= 80, f"WebMasters-like vacancy must score >= 80, got {score}"
    assert "AI-автоматизации" in reasons
    assert "боты/AI-ассистенты" in reasons
    assert "контентная упаковка" in reasons


def test_russian_ai_keywords_score_high():
    """Vacancy with Russian AI/automation keywords gets a high score."""
    engine = ScoringEngine()
    score, reasons = engine.score(
        {
            "name": "AI-разработчик",
            "snippet_requirement": (
                "Нейросети, автоворонки, AI-агенты, боты, "
                "no-code/low-code, инструкции, кейсы, Python, OpenAI"
            ),
            "schedule": "удалённо",
        }
    )
    assert score >= 50, f"Russian AI keywords should give a high score, got {score}"
    assert (
        "нейросети/LLM" in reasons
        or "AI-агенты/ассистенты" in reasons
    )
    assert "no-code/low-code" in reasons


def test_python_automation_vacancy_scores_well():
    engine = ScoringEngine()
    score, reasons = engine.score(
        {
            "name": "Python Automation Engineer",
            "snippet_requirement": "Python, FastAPI, REST API, Telegram bots, integrations",
            "snippet_responsibility": "Build AI automation, internal tools",
            "schedule": "remote",
        }
    )
    assert score >= 45
    assert "Python/API/интеграции" in reasons
    assert "AI-автоматизации" in reasons


# ---------------------------------------------------------------------------
# ScoringEngine - irrelevant vacancies
# ---------------------------------------------------------------------------


def test_1c_accountant_does_not_score_high():
    engine = ScoringEngine()
    score, _ = engine.score(
        {
            "name": "1С Бухгалтер",
            "snippet_requirement": "1С 8.3, бухучёт, отчётность",
            "snippet_responsibility": "Ведение бухгалтерии, работа с документами",
        }
    )
    assert score < 30, f"1С vacancy must score low, got {score}"


def test_java_backend_does_not_score_high():
    engine = ScoringEngine()
    score, _ = engine.score(
        {
            "name": "Senior Java Backend Developer",
            "snippet_requirement": "Java, Spring Boot, PostgreSQL, более 5 лет опыта",
            "snippet_responsibility": "Java backend development",
            "schedule": "офис",
        }
    )
    assert score < 30, f"Java backend vacancy must score low, got {score}"


def test_pure_frontend_role_does_not_score_high():
    engine = ScoringEngine()
    score, _ = engine.score(
        {
            "name": "Frontend разработчик",
            "snippet_requirement": "React, Vue, TypeScript",
            "snippet_responsibility": "Верстальщик и frontend-разработчик",
        }
    )
    assert score < 30


# ---------------------------------------------------------------------------
# ScoringEngine - bounds and structure
# ---------------------------------------------------------------------------


def test_score_is_clamped_to_0_100():
    engine = ScoringEngine()
    score, _ = engine.score({"name": "", "snippet_requirement": ""})
    assert 0 <= score <= 100

    overloaded = engine.score(
        {
            "name": "AI-автоматизации, нейросети, AI-агенты, ассистенты, боты, чат-боты",
            "snippet_requirement": "Python, FastAPI, REST API, OpenAI, n8n, Make, "
            "no-code/low-code, автоворонки, интеграции, генерация контента",
            "snippet_responsibility": "MVP, гипотезы, инструкции, гайды, кейсы, "
            "контент, маркетинг, база знаний, презентации, описание продуктов",
            "schedule": "удалённо, гибрид",
        }
    )
    assert 0 <= overloaded[0] <= 100


def test_reasons_are_unique_and_in_russian():
    engine = ScoringEngine()
    score, reasons = engine.score(
        {
            "name": "AI Automation Engineer",
            "snippet_requirement": "AI-автоматизации, AI-агенты, AI-ассистенты",
        }
    )
    assert score > 0
    # No duplicates
    assert len(reasons) == len(set(reasons))
    # Russian reason labels expected
    assert any("AI" in r for r in reasons)


def test_handles_html_tags_in_description():
    engine = ScoringEngine()
    score, reasons = engine.score(
        {
            "name": "AI Automation",
            "description": "<p>Будем строить <b>AI-агентов</b>, "
            "<i>ботов</i>, автоворонки и интеграции.</p>",
        }
    )
    assert score > 0
    assert (
        "AI-агенты/ассистенты" in reasons
        or "боты/AI-ассистенты" in reasons
    )


def test_handles_yo_letter():
    engine = ScoringEngine()
    score, _ = engine.score({"name": "Удалёнка", "schedule": "удалённо"})
    assert score >= 4  # the udalyonka bonus


def test_office_only_penalty_applied():
    engine = ScoringEngine()
    # Pure office-only role with no AI signal -> penalty triggers, score low.
    score, reasons = engine.score(
        {
            "name": "Офис-менеджер",
            "snippet_requirement": "Работа в офисе, документы",
            "schedule": "офис",
        }
    )
    assert score < 20
    assert "офис-only" in reasons or score == 0


def test_scoring_returns_tuple_int_list():
    engine = ScoringEngine()
    score, reasons = engine.score({"name": "test"})
    assert isinstance(score, int)
    assert isinstance(reasons, list)
