from app.scoring.engine import ScoringEngine


def test_scoring_engine_scores_keywords() -> None:
    engine = ScoringEngine()
    score, reasons = engine.score(
        {
            "name": "Python FastAPI Engineer",
            "snippet_requirement": "AI automation",
            "schedule": "remote",
        }
    )
    assert score == 85
    assert "Python" in reasons
    assert "FastAPI" in reasons


def test_scoring_engine_caps_at_100() -> None:
    engine = ScoringEngine()
    score, _ = engine.score(
        {
            "name": "Python FastAPI AI automation remote",
            "snippet_requirement": "удаленная работа",
        }
    )
    assert score == 95
