# Scoring Engine — Stage 2
# Оценивает вакансию под профиль пользователя (0–100)

class ScoringEngine:
    """Scores a vacancy against user profile."""

    def score(self, vacancy: dict) -> tuple[int, list[str]]:
        """
        Returns (score, reasons).
        Example: (82, ["Python + FastAPI", "AI automation", "remote"])
        """
        raise NotImplementedError("Scoring engine — Stage 2")
