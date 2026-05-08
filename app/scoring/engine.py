"""Scoring Engine — Stage 2."""

from __future__ import annotations


class ScoringEngine:
    """Rule-based scoring (0-100) for vacancy relevance."""

    KEYWORDS: dict[str, tuple[int, str]] = {
        "python": (25, "Python"),
        "fastapi": (15, "FastAPI"),
        "ai": (20, "AI"),
        "automation": (15, "automation"),
        "remote": (10, "remote"),
        "удален": (10, "remote"),
    }

    def score(self, vacancy: dict) -> tuple[int, list[str]]:
        parts = [
            str(vacancy.get("name", "")),
            str(vacancy.get("snippet_requirement", "")),
            str(vacancy.get("snippet_responsibility", "")),
            str(vacancy.get("schedule", "")),
        ]
        text = " ".join(parts).lower()

        score = 0
        reasons: list[str] = []
        for kw, (points, reason) in self.KEYWORDS.items():
            if kw in text:
                score += points
                reasons.append(reason)

        return min(score, 100), reasons
