"""Tests for app/scoring/calibration.py (Stage 4)."""

from __future__ import annotations

from app.scoring.calibration import calibrate


def test_empty_text_no_change():
    assert calibrate(50, "") == 50


def test_irrelevant_text_no_change():
    assert calibrate(50, "разработчик на java spring boot") == 50


def test_automation_api_combo_boost():
    score = calibrate(50, "автоматизация процессов api интеграция webhook")
    assert score > 50


def test_telegram_bot_combo_boost():
    score = calibrate(50, "разработка telegram bot python")
    assert score > 50


def test_google_sheets_automation_boost():
    score = calibrate(50, "google sheets автоматизация отчётности")
    assert score > 50


def test_llm_workflow_platform_boost():
    score = calibrate(50, "llm pipeline workflow оркестра агентов")
    assert score > 50


def test_openai_workflow_boost():
    score = calibrate(50, "openai gpt workflow платформа автоматизации")
    assert score > 50


def test_strict_experience_gate_penalty():
    score = calibrate(80, "опыт от 5 лет разработки")
    assert score < 80


def test_min_5_years_penalty():
    score = calibrate(70, "не менее 5 лет опыта")
    assert score < 70


def test_minimum_5_years_penalty():
    score = calibrate(60, "минимум 5 лет коммерческого опыта")
    assert score < 60


def test_academic_research_penalty():
    score = calibrate(50, "публикации в научных журналах конференции")
    assert score < 50


def test_arxiv_penalty():
    score = calibrate(60, "arxiv статьи научн исследования")
    assert score < 60


def test_floor_clamp():
    assert calibrate(0, "публикации конференции arxiv не менее 5 лет") == 0


def test_ceiling_clamp():
    assert calibrate(100, "telegram bot api интеграция google sheets автоматизация") == 100


def test_near_ceiling_does_not_exceed_100():
    score = calibrate(95, "telegram bot api интеграция google sheets автоматизация llm workflow")
    assert score <= 100


def test_near_floor_does_not_go_below_0():
    score = calibrate(5, "публикации конференции arxiv не менее 5 лет")
    assert score >= 0


def test_automation_without_api_no_boost():
    # Only "автоматизац" present but not the required "api интегра" / "rest api" / "webhook"
    score_with = calibrate(50, "автоматизация api интеграция")
    score_without = calibrate(50, "автоматизация бизнес процессов")
    assert score_with > score_without


def test_telegram_without_bot_no_boost():
    # "telegram" alone without "бот"/"bot" should not trigger the combo boost
    score_with_bot = calibrate(50, "telegram bot разработчик")
    score_without_bot = calibrate(50, "telegram канал публикации")
    assert score_with_bot > score_without_bot


def test_calibrate_returns_int():
    result = calibrate(50, "automation api")
    assert isinstance(result, int)
