"""Scoring Engine — Stage 3."""

from __future__ import annotations


class ScoringEngine:
    """Rule-based scoring (0-100) for vacancy relevance."""

    POSITIVE_KEYWORDS: dict[str, tuple[int, str]] = {
        "python": (20, "Python"),
        "fastapi": (10, "FastAPI"),
        "telegram": (10, "Telegram"),
        "google sheets": (12, "Google Sheets API"),
        "api": (8, "API integrations"),
        "ai": (14, "AI"),
        "automation": (14, "automation"),
        "e-commerce": (8, "e-commerce"),
        "ecommerce": (8, "e-commerce"),
        "marketplace": (10, "marketplace"),
        "remote": (10, "remote"),
        "удален": (10, "remote"),
    }

    NEGATIVE_KEYWORDS: dict[str, tuple[int, str]] = {
        "call-center": (-25, "call-center penalty"),
        "колл-центр": (-25, "call-center penalty"),
        "sales": (-20, "sales-heavy penalty"),
        "продаж": (-20, "sales-heavy penalty"),
        "support only": (-20, "support-only penalty"),
        "только поддержка": (-20, "support-only penalty"),
        "оператор": (-15, "operator penalty"),
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
        for kw, (points, reason) in self.POSITIVE_KEYWORDS.items():
            if kw in text:
                score += points
                reasons.append(reason)

        for kw, (points, reason) in self.NEGATIVE_KEYWORDS.items():
            if kw in text:
                score += points
                reasons.append(reason)

        return max(0, min(score, 100)), reasons
