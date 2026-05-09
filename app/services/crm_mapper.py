from __future__ import annotations

from datetime import datetime, timezone

from app.services.job_crm import REQUIRED_COLUMNS
from app.services.vacancy import Vacancy

# New canonical header order matches REQUIRED_COLUMNS in job_crm.py
CRM_HEADERS = tuple(REQUIRED_COLUMNS)

# Legacy alias kept for backward-compatible tests / tooling
CRM_HEADERS_LEGACY = ("date", "vacancy", "company", "url", "score", "status", "reason", "cover_letter")


def vacancy_to_crm_job(
    vacancy: Vacancy,
    score: int,
    reasons: list[str],
    status: str,
    tags: str = "",
    letter: str = "",
    notes: str = "",
) -> dict[str, str]:
    """Return a job dict ready for JobCRM.upsert_job."""
    from app.services.job_crm import extract_vacancy_id

    vacancy_id = vacancy.id or extract_vacancy_id(vacancy.url)
    now = datetime.now(timezone.utc).isoformat()
    return {
        "date": now,
        "vacancy_id": vacancy_id,
        "Name": vacancy.name,
        "Company": vacancy.employer,
        "Link": vacancy.url,
        "Score": str(score),
        "status": status,
        "Tags": tags or ", ".join(reasons[:3]),
        "Letter": letter,
        "notes": notes,
        "updated_at": now,
    }


def vacancy_to_crm_row(vacancy: Vacancy, score: int, reasons: list[str], status: str) -> list[str]:
    """Legacy helper — returns a flat row in old 8-column format.

    Kept for backward compatibility with existing tests that call this
    function directly.  New code should use vacancy_to_crm_job instead.
    """
    return [
        datetime.now(timezone.utc).isoformat(),
        vacancy.name,
        vacancy.employer,
        vacancy.url,
        str(score),
        status,
        ", ".join(reasons[:3]),
        "",  # cover_letter — filled separately
    ]
