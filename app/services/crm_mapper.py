from __future__ import annotations

from datetime import datetime, timezone

from app.services.vacancy import Vacancy


CRM_HEADERS = ("date", "vacancy", "company", "url", "score", "status", "reason", "cover_letter", "response", "published_at")


def vacancy_to_crm_row(vacancy: Vacancy, score: int, reasons: list[str], status: str) -> list[str]:
    return [
        datetime.now(timezone.utc).isoformat(),
        vacancy.name,
        vacancy.employer,
        vacancy.url,
        str(score),
        status,
        ", ".join(reasons[:3]),
        "",
        "",
        vacancy.published_at or "",
    ]
