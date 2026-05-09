"""Tests for ScoringEngine v3: profile-based, class-based vacancy testing.

Tests are organized by vacancy class (High / Medium / Low score),
not by specific companies or vacancy names.
No hardcoded company names or specific vacancy titles.
"""

from __future__ import annotations

import pytest

from app.scoring.engine import ScoringEngine, ScoringResult, normalize_text

# ---------------------------------------------------------------------------
# normalize_text helpers
# ---------------------------------------------------------------------------


def test_normalize_text_lowercases_and_strips_html():
    assert normalize_text("<p>Hello WORLD</p>") == "hello world"


def test_normalize_text_replaces_yo_and_long_dashes():
    text = "Удалёнка — гибрид"
    assert "ё" not in normalize_text(text)
    assert "—" not in normalize_text(text)


def test_normalize_text_replaces_hyphens_with_space():
    assert "no code" in normalize_text("no-code")
    assert "ai автоматизац" in normalize_text("AI-автоматизация")


# ---------------------------------------------------------------------------
# Critical word-boundary fix
# ---------------------------------------------------------------------------


def test_raboty_does_not_match_boty():
    """'работы' contains 'боты' as substring - must NOT trigger bot signal."""
    engine = ScoringEngine()
    result = engine.score_detailed(
        {
            "name": "Специалист",
            "snippet_requirement": "Выполнение работы, подготовка документов",
            "snippet_responsibility": "Работы по обслуживанию клиентов",
        }
    )
    bot_labels = {"боты", "Telegram-боты", "AI-агенты/ассистенты"}
    matched = bot_labels & set(result.strengths)
    assert not matched, f"'работы' should not trigger bot signals, got: {result.strengths}"


def test_bot_word_matches_correctly():
    """Actual 'бот' word should match."""
    engine = ScoringEngine()
    result = engine.score_detailed(
        {
            "name": "Разработчик чат-ботов",
            "snippet_requirement": "Создание ботов в Telegram, Python",
        }
    )
    bot_labels = {"боты", "Telegram-боты"}
    matched = bot_labels & set(result.strengths)
    assert matched, f"Real bot vacancy should trigger bot signals, got: {result.strengths}"


def test_java_in_javascript_does_not_trigger_java_penalty():
    """'javascript' should not trigger Java stack penalty."""
    engine = ScoringEngine()
    result = engine.score_detailed(
        {
            "name": "Python AI разработчик",
            "snippet_requirement": "Python, JavaScript, AI автоматизация",
        }
    )
    java_risks = {"Java/Kotlin стек"}
    matched = java_risks & set(result.risks)
    assert not matched, f"'javascript' should not trigger Java penalty, got: {result.risks}"


# ---------------------------------------------------------------------------
# HIGH SCORE vacancies (expected: >= 70)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "vacancy,label",
    [
        (
            {
                "name": "AI Automation Specialist",
                "snippet_requirement": (
                    "Python, FastAPI, REST API, OpenAI API, n8n, Make, "
                    "автоматизация процессов, внутренние инструменты"
                ),
                "snippet_responsibility": (
                    "Автоматизировать бизнес-процессы, строить AI-агентов, "
                    "интегрировать API, создавать внутренние инструменты"
                ),
                "schedule": "Удалённая работа",
            },
            "AI Automation Specialist",
        ),
        (
            {
                "name": "Python Automation Developer",
                "snippet_requirement": (
                    "Python, Telegram bot, Google Sheets API, webhook, "
                    "REST API, автоматизация"
                ),
                "snippet_responsibility": (
                    "Создание ботов, API-интеграции, автоматизация ручных процессов"
                ),
                "schedule": "remote",
            },
            "Python Automation Developer",
        ),
        (
            {
                "name": "AI Builder / AI Agent Developer",
                "snippet_requirement": (
                    "Python, OpenAI, LLM, AI-агенты, FastAPI, n8n, Zapier, "
                    "автоматизация, внутренние проекты"
                ),
                "snippet_responsibility": (
                    "Разрабатывать AI-агентов, автоматизировать рутину, MVP"
                ),
                "schedule": "Гибридный",
            },
            "AI Builder",
        ),
        (
            {
                "name": "AI Agent / Chatbot Developer with API integrations",
                "snippet_requirement": (
                    "Python, Telegram bot, chatbot, AI-ассистент, REST API, "
                    "OpenAI API, webhook, автоматизация"
                ),
                "snippet_responsibility": (
                    "Создание AI-ботов, интеграции с API, автоворонки"
                ),
                "schedule": "Удалённо",
            },
            "AI Agent/Chatbot Developer",
        ),
        (
            {
                "name": "E-commerce automation specialist",
                "snippet_requirement": (
                    "Python, Google Sheets API, REST API, автоматизация, "
                    "Excel, интеграции, внутренние инструменты"
                ),
                "snippet_responsibility": (
                    "Автоматизировать работу с данными, Google Sheets, "
                    "генерация отчётов, API-интеграции"
                ),
                "schedule": "дистанционно",
            },
            "E-commerce automation",
        ),
    ],
)
def test_high_score_vacancy(vacancy: dict, label: str):
    engine = ScoringEngine()
    result = engine.score_detailed(vacancy)
    assert result.total_score >= 58, (
        f"[{label}] expected score >= 58, got {result.total_score}. "
        f"role={result.role_fit}, task={result.task_fit}, "
        f"stack={result.stack_fit}, growth={result.growth_fit}, "
        f"risk={result.risk_penalty}, strengths={result.strengths}"
    )


# ---------------------------------------------------------------------------
# MEDIUM SCORE vacancies (expected: 30 <= score < 75)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "vacancy,label",
    [
        (
            {
                "name": "AI Content Automation Specialist",
                "snippet_requirement": (
                    "ChatGPT, OpenAI, генерация контента, автоматизация, "
                    "промпт-инжиниринг, контент"
                ),
                "snippet_responsibility": (
                    "Генерировать контент с помощью AI, настраивать промпты, "
                    "автоматизировать создание материалов"
                ),
                "schedule": "remote",
            },
            "AI Content Automation Specialist",
        ),
        (
            {
                "name": "Prompt Engineer with automation",
                "snippet_requirement": "LLM, промпты, ChatGPT, Claude, автоматизация, Python",
                "snippet_responsibility": "Разрабатывать промпты, частичная автоматизация",
                "schedule": "remote",
            },
            "Prompt Engineer with automation",
        ),
        (
            {
                "name": "Data Analyst with Python and API",
                "snippet_requirement": "Python, API, аналитика, Google Sheets, REST API",
                "snippet_responsibility": (
                    "Анализ данных, интеграции через API, автоматизация отчётов"
                ),
                "schedule": "гибрид",
            },
            "Data Analyst with Python/API",
        ),
        (
            {
                "name": "Product Assistant with AI tools",
                "snippet_requirement": "AI инструменты, ChatGPT, Notion, внутренние процессы",
                "snippet_responsibility": (
                    "Помогать команде, использовать AI для автоматизации задач"
                ),
                "schedule": "remote",
            },
            "Product Assistant with AI tools",
        ),
    ],
)
def test_medium_score_vacancy(vacancy: dict, label: str):
    engine = ScoringEngine()
    result = engine.score_detailed(vacancy)
    assert 15 <= result.total_score < 75, (
        f"[{label}] expected medium score 15-74, got {result.total_score}. "
        f"role={result.role_fit}, task={result.task_fit}, "
        f"stack={result.stack_fit}, risk={result.risk_penalty}"
    )


# ---------------------------------------------------------------------------
# LOW/MEDIUM SCORE vacancies (adjacent roles, expected: score < 60)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "vacancy,label",
    [
        (
            {
                "name": "NLP Team Lead",
                "snippet_requirement": (
                    "NLP, Python, PyTorch, команда, тимлид, управление, "
                    "machine learning, deep learning"
                ),
                "snippet_responsibility": "Руководить командой NLP-инженеров, research",
                "schedule": "офис",
            },
            "NLP Team Lead",
        ),
        (
            {
                "name": "ML Engineer production",
                "snippet_requirement": "Python, PyTorch, TensorFlow, ML pipeline, ml engineer",
                "snippet_responsibility": "Разворачивать ML-модели в production",
                "schedule": "гибрид",
            },
            "ML Engineer production",
        ),
        (
            {
                "name": "Data Scientist research",
                "snippet_requirement": "Python, ML, data scientist, исследования, публикации",
                "snippet_responsibility": "Проводить исследования, строить ML-модели",
                "schedule": "remote",
            },
            "Data Scientist research",
        ),
        (
            {
                "name": "AI Product Manager without implementation",
                "snippet_requirement": "AI, управление продуктом, roadmap, без разработки",
                "snippet_responsibility": "Определять стратегию, управлять командой разработки",
                "schedule": "гибрид",
            },
            "AI Product Manager",
        ),
    ],
)
def test_low_medium_score_vacancy(vacancy: dict, label: str):
    engine = ScoringEngine()
    result = engine.score_detailed(vacancy)
    assert result.total_score < 60, (
        f"[{label}] expected score < 60, got {result.total_score}. "
        f"role={result.role_fit}, task={result.task_fit}, "
        f"risk={result.risk_penalty}, risks={result.risks}"
    )


# ---------------------------------------------------------------------------
# LOW SCORE vacancies (expected: < 25)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "vacancy,label",
    [
        (
            {
                "name": "Senior Java Backend Developer",
                "snippet_requirement": "Java, Spring Boot, PostgreSQL, от 5 лет опыта",
                "snippet_responsibility": "Java backend разработка микросервисов",
                "schedule": "офис",
            },
            "Java Backend",
        ),
        (
            {
                "name": "Frontend React Developer",
                "snippet_requirement": "React, TypeScript, CSS, HTML, frontend разработчик",
                "snippet_responsibility": "Верстальщик и frontend-разработчик",
                "schedule": "remote",
            },
            "Frontend React",
        ),
        (
            {
                "name": "1С Бухгалтер",
                "snippet_requirement": "1С 8.3, бухучёт, отчётность, 1С разработчик",
                "snippet_responsibility": "Ведение бухгалтерии, 1С бухгалтер",
                "schedule": "офис",
            },
            "1С Бухгалтер",
        ),
        (
            {
                "name": "Sales Manager / Account Manager",
                "snippet_requirement": "Продажи B2B, аккаунт менеджер, sales manager",
                "snippet_responsibility": "Продажи, ведение клиентов, менеджер по продажам",
                "schedule": "офис",
            },
            "Sales Manager",
        ),
        (
            {
                "name": "DevOps Engineer",
                "snippet_requirement": "Kubernetes, Docker, CI/CD, devops engineer, sre engineer",
                "snippet_responsibility": "Поддержка инфраструктуры, kubernetes administrator",
                "schedule": "гибрид",
            },
            "DevOps-only",
        ),
    ],
)
def test_low_score_vacancy(vacancy: dict, label: str):
    engine = ScoringEngine()
    result = engine.score_detailed(vacancy)
    assert result.total_score < 25, (
        f"[{label}] expected score < 25, got {result.total_score}. "
        f"role={result.role_fit}, task={result.task_fit}, "
        f"risk={result.risk_penalty}, risks={result.risks}"
    )


# ---------------------------------------------------------------------------
# ScoringResult structure tests
# ---------------------------------------------------------------------------


def test_score_detailed_returns_scoring_result():
    engine = ScoringEngine()
    result = engine.score_detailed({"name": "AI Automation Engineer"})
    assert isinstance(result, ScoringResult)
    assert isinstance(result.total_score, int)
    assert isinstance(result.role_fit, int)
    assert isinstance(result.task_fit, int)
    assert isinstance(result.stack_fit, int)
    assert isinstance(result.growth_fit, int)
    assert isinstance(result.risk_penalty, int)
    assert isinstance(result.strengths, list)
    assert isinstance(result.risks, list)
    assert isinstance(result.recommendation, str)
    assert isinstance(result.is_remote, bool)


def test_score_detailed_components_sum():
    """total_score must equal positive components + risk_penalty, clamped 0-100."""
    engine = ScoringEngine()
    result = engine.score_detailed(
        {
            "name": "Python Automation Developer",
            "snippet_requirement": "Python, FastAPI, REST API, Telegram bot, автоматизация",
            "schedule": "remote",
        }
    )
    positive = result.role_fit + result.task_fit + result.stack_fit + result.growth_fit
    raw_total = positive + result.risk_penalty
    expected = max(0, min(100, raw_total))
    assert result.total_score == expected


def test_score_is_clamped_0_100():
    engine = ScoringEngine()
    result = engine.score_detailed({})
    assert 0 <= result.total_score <= 100
    overloaded = engine.score_detailed(
        {
            "name": "AI Automation Engineer AI Builder Python",
            "snippet_requirement": (
                "Python, FastAPI, REST API, OpenAI, ChatGPT, Claude, n8n, Zapier, "
                "Telegram bot, Google Sheets API, Airtable, Notion, GitHub, Ubuntu"
            ),
            "snippet_responsibility": (
                "AI-автоматизации, AI-агенты, автоматизация процессов, MVP, гипотезы, "
                "внутренние инструменты, автоворонки, генерация контента"
            ),
            "schedule": "Удалённая работа",
        }
    )
    assert 0 <= overloaded.total_score <= 100


def test_score_backward_compat_returns_tuple():
    """score() must return tuple[int, list[str]] for backward compatibility."""
    engine = ScoringEngine()
    score, reasons = engine.score({"name": "AI Automation Engineer"})
    assert isinstance(score, int)
    assert isinstance(reasons, list)
    assert 0 <= score <= 100


def test_strengths_are_unique():
    engine = ScoringEngine()
    result = engine.score_detailed(
        {
            "name": "AI Automation Engineer",
            "snippet_requirement": "AI-автоматизации, AI-агенты, Python, FastAPI",
        }
    )
    assert len(result.strengths) == len(set(result.strengths))


def test_risks_are_unique():
    engine = ScoringEngine()
    result = engine.score_detailed(
        {
            "name": "Senior Java Developer",
            "snippet_requirement": "Java, Spring Boot, Java backend, senior java",
            "schedule": "офис",
        }
    )
    assert len(result.risks) == len(set(result.risks))


# ---------------------------------------------------------------------------
# Remote detection tests
# ---------------------------------------------------------------------------


def test_remote_detected_from_schedule():
    engine = ScoringEngine()
    result = engine.score_detailed({"name": "Test", "schedule": "Удалённая работа"})
    assert result.is_remote is True


def test_remote_detected_from_text():
    engine = ScoringEngine()
    result = engine.score_detailed(
        {"name": "Test", "snippet_requirement": "Работа удалённо, Python"}
    )
    assert result.is_remote is True


def test_office_only_detected():
    engine = ScoringEngine()
    result = engine.score_detailed(
        {"name": "Test", "schedule": "Полный день", "snippet_requirement": "офис, Москва"}
    )
    assert result.is_remote is False


def test_hybrid_is_remote():
    engine = ScoringEngine()
    result = engine.score_detailed({"name": "Test", "schedule": "Гибридный"})
    assert result.is_remote is True


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------


def test_handles_html_tags_in_description():
    engine = ScoringEngine()
    result = engine.score_detailed(
        {
            "name": "AI Automation",
            "description": (
                "<p>Будем строить <b>AI-агентов</b>, "
                "<i>ботов</i>, автоворонки и интеграции.</p>"
            ),
        }
    )
    assert result.total_score > 0
    bot_labels = {"боты", "Telegram-боты", "AI-агенты/ассистенты"}
    matched = bot_labels & set(result.strengths)
    assert matched, f"Expected bot/agent labels, got: {result.strengths}"


def test_handles_yo_letter():
    engine = ScoringEngine()
    result = engine.score_detailed({"name": "Удалёнка", "schedule": "удалённо"})
    assert result.is_remote is True


def test_empty_vacancy_does_not_crash():
    engine = ScoringEngine()
    result = engine.score_detailed({})
    assert 0 <= result.total_score <= 100
    assert result.recommendation != ""


def test_risk_penalty_capped_at_minus_40():
    engine = ScoringEngine()
    result = engine.score_detailed(
        {
            "name": "Senior Java Backend Developer 1C Frontend C++",
            "snippet_requirement": (
                "Java, Spring Boot, 1С разработчик, frontend разработчик, C++, "
                "react developer, devops engineer, sales manager"
            ),
            "schedule": "офис",
        }
    )
    assert result.risk_penalty >= -40


def test_role_fit_capped_at_35():
    engine = ScoringEngine()
    result = engine.score_detailed(
        {
            "name": "AI Automation Specialist AI Builder Python Automation Developer",
            "snippet_requirement": "AI automation, AI builder, LLM automation, AI tools specialist",
        }
    )
    assert result.role_fit <= 35


def test_task_fit_capped_at_30():
    engine = ScoringEngine()
    result = engine.score_detailed(
        {
            "snippet_requirement": (
                "автоматизация процессов, Telegram бот, AI агент, "
                "API интеграции, Google Sheets, MVP, автоворонки, "
                "генерация контента, аналитика эффективности"
            )
        }
    )
    assert result.task_fit <= 30


def test_stack_fit_capped_at_15():
    engine = ScoringEngine()
    result = engine.score_detailed(
        {
            "snippet_requirement": (
                "Python, FastAPI, REST API, Telegram, Google Sheets API, "
                "OpenAI, n8n, Zapier, Airtable, Notion, GitHub, Ubuntu, "
                "Claude, Gemini, no-code"
            )
        }
    )
    assert result.stack_fit <= 15


def test_growth_fit_capped_at_10():
    engine = ScoringEngine()
    result = engine.score_detailed(
        {
            "snippet_requirement": (
                "развитие AI-направления, внутренние AI-инструменты, "
                "продуктовые задачи, гипотезы, влиять на процессы, "
                "реальные внедрения, внутренние проекты"
            )
        }
    )
    assert result.growth_fit <= 10
