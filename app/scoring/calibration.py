"""Calibration layer for Stage 4.

Applies compound-signal boosts and penalties on top of ScoringEngine's
base score.  Targets signals not already covered by single-term engine rules
to avoid double-counting.

Usage::

    from app.scoring.calibration import calibrate

    calibrated = calibrate(result.total_score, raw_vacancy_text)
"""

from __future__ import annotations

from app.scoring.engine import normalize_text

# Boosts: compound signals — engine scores individual terms;
# calibration rewards co-occurrence of related signals.
_BOOSTS: list[tuple[tuple[str, ...], tuple[str, ...], int]] = [
    # automation + API integration combo
    (
        ("автоматизац",),
        ("api интегра", "rest api", "webhook"),
        5,
    ),
    # Telegram bot builder (engine has +2 Telegram stack, +7 AI task;
    # calibration rewards the explicit bot-builder framing)
    (
        ("telegram",),
        ("бот", "bot"),
        4,
    ),
    # Google Sheets workflow integration
    (
        ("google sheets", "sheets"),
        ("автоматизац",),
        4,
    ),
    # LLM workflow / orchestration platform (not just mentioning LLM)
    (
        ("llm", "gpt", "openai", "claude"),
        ("pipeline", "workflow", "платформ", "оркестра"),
        6,
    ),
]

# Penalties: phrases NOT in engine's risk rules to avoid double-count.
# Engine already penalises "5+ лет", "от 5 лет" in _SENIOR_ONLY_PATTERNS;
# calibration adds penalty for complementary phrasing.
_PENALTIES: list[tuple[tuple[str, ...], int]] = [
    (
        ("опыт от 5", "не менее 5 лет", "минимум 5 лет"),
        -8,
    ),
    (
        ("публикаци", "конференц", "arxiv", "научн статья"),
        -6,
    ),
]


def _any_match(text: str, terms: tuple[str, ...]) -> bool:
    return any(t in text for t in terms)


def calibrate(base_score: int, text: str) -> int:
    """Apply calibration boosts and penalties on top of base_score.

    Args:
        base_score: raw total_score from ScoringEngine.score_detailed()
        text: raw vacancy text (will be normalized internally)

    Returns:
        Adjusted score clamped to [0, 100].
    """
    norm = normalize_text(text)
    delta = 0

    for must_all, must_any, pts in _BOOSTS:
        if _any_match(norm, must_all) and _any_match(norm, must_any):
            delta += pts

    for terms, pen in _PENALTIES:
        if _any_match(norm, terms):
            delta += pen

    return max(0, min(100, base_score + delta))
