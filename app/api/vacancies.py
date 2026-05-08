"""API роутер для вакансий."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from app.services.hh_client import HHClient, HHClientError
from app.services.vacancy import Vacancy

router = APIRouter(prefix="/vacancies", tags=["vacancies"])


@router.get("")
async def search_vacancies(
    text: str = Query(default="Python AI automation", description="Поисковый запрос"),
    area: int | None = Query(default=None, description="ID региона: 1=Москва, 113=Россия"),
    salary: int | None = Query(default=None, description="Мин. зарплата"),
    schedule: str | None = Query(default=None, description="remote | fullDay | flexible"),
    per_page: int = Query(default=10, ge=1, le=100),
    page: int = Query(default=0, ge=0),
) -> dict:
    """Поиск вакансий через HH API."""
    client = HHClient()
    try:
        raw = await client.search_vacancies(
            text=text,
            area=area,
            salary=salary,
            schedule=schedule,
            per_page=per_page,
            page=page,
        )
    except HHClientError as e:
        raise HTTPException(status_code=502, detail=str(e)) from e

    items = [Vacancy.from_hh(v) for v in raw.get("items", [])]
    return {
        "found": raw.get("found", 0),
        "page": raw.get("page", 0),
        "pages": raw.get("pages", 0),
        "per_page": raw.get("per_page", 0),
        "items": [v.model_dump() for v in items],
    }
