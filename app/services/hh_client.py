"""HeadHunter API client.

Stage 1: публичный поиск вакансий без авторизации.
Документация: https://api.hh.ru/openapi/redoc
"""

from __future__ import annotations

from typing import Any

import httpx

from app.core.config import settings
from app.core.logging import logger


class HHClientError(Exception):
    """Базовая ошибка HH клиента."""


class HHClient:
    """Асинхронный клиент для HeadHunter API.

    Используется без авторизации (публичный поиск). Для поиска
    OAuth не требуется — нужен только корректный User-Agent.
    """

    def __init__(
        self,
        base_url: str | None = None,
        user_agent: str | None = None,
        access_token: str | None = None,
        timeout: float = 10.0,
    ) -> None:
        self.base_url = (base_url or settings.hh_base_url).rstrip("/")
        self.user_agent = user_agent or settings.hh_user_agent
        self.access_token = access_token or settings.hh_access_token
        self.timeout = timeout

    def _headers(self) -> dict[str, str]:
        headers = {
            "User-Agent": self.user_agent,
            "Accept": "application/json",
        }
        if self.access_token:
            headers["Authorization"] = f"Bearer {self.access_token}"
        return headers

    async def _get(self, path: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        url = f"{self.base_url}{path}"
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                response = await client.get(url, params=params, headers=self._headers())
                response.raise_for_status()
                return response.json()
            except httpx.HTTPStatusError as e:
                logger.error(f"HH API error {e.response.status_code}: {e.response.text[:200]}")
                raise HHClientError(f"HH API returned {e.response.status_code}") from e
            except httpx.RequestError as e:
                logger.error(f"HH API request failed: {e}")
                raise HHClientError(f"HH API request failed: {e}") from e

    async def search_vacancies(
        self,
        text: str | None = None,
        area: int | None = None,
        salary: int | None = None,
        only_with_salary: bool = False,
        experience: str | None = None,
        schedule: str | None = None,
        employment: str | None = None,
        per_page: int = 20,
        page: int = 0,
        **extra: Any,
    ) -> dict[str, Any]:
        """Поиск вакансий.

        Параметры HH API:
            text:       поисковый запрос (например, "Python AI automation")
            area:       ID региона (1 = Москва, 2 = СПб, 113 = Россия)
            salary:     минимальная зарплата
            experience: noExperience | between1And3 | between3And6 | moreThan6
            schedule:   fullDay | shift | flexible | remote | flyInFlyOut
            employment: full | part | project | volunteer | probation
            per_page:   до 100
            page:       страница (с 0)

        Возвращает сырой JSON из HH API: {items, found, pages, page, per_page}.
        """
        params: dict[str, Any] = {"per_page": per_page, "page": page}
        if text:
            params["text"] = text
        if area is not None:
            params["area"] = area
        if salary is not None:
            params["salary"] = salary
        if only_with_salary:
            params["only_with_salary"] = "true"
        if experience:
            params["experience"] = experience
        if schedule:
            params["schedule"] = schedule
        if employment:
            params["employment"] = employment
        params.update(extra)

        logger.info(f"HH search: {params}")
        data = await self._get("/vacancies", params=params)
        logger.info(f"HH search returned {len(data.get('items', []))} items (found={data.get('found')})")
        return data

    async def get_vacancy(self, vacancy_id: str) -> dict[str, Any]:
        """Получить полные данные вакансии по ID (с описанием)."""
        return await self._get(f"/vacancies/{vacancy_id}")
