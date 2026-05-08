from app.scoring.engine import ScoringEngine


def test_scoring_engine_boosts_target_stack() -> None:
    engine = ScoringEngine()
    score, reasons = engine.score(
        {
            "name": "Python FastAPI Telegram AI automation engineer",
            "snippet_requirement": "Google Sheets API, marketplace, remote",
        }
    )
    assert score >= 80
    assert "Python" in reasons
    assert "Google Sheets API" in reasons


def test_scoring_engine_applies_negative_penalties() -> None:
    engine = ScoringEngine()
    score, reasons = engine.score(
        {
            "name": "Sales call-center operator",
            "snippet_requirement": "только поддержка клиентов",
        }
    )
    assert score == 0
    assert any("penalty" in reason for reason in reasons)
