"""HeadHunter API client.

HH_ACCESS_TOKEN (app token) is required for authorized requests.
Without a token, /vacancies returns 403 Forbidden.

Get a token:  python scripts/get_hh_app_token.py
Check API:    python scripts/check_hh_api.py

Docs: https://api.hh.ru/openapi/redoc
"""

from __future__ import annotations

from typing import Any

import httpx

from app.core.config import settings
from app.core.logging import logger


class HHClientError(Exception):
    """Base error for HH client."""


class HHClient:
    """Async client for HeadHunter API.

    Searching vacancies (/vacancies) requires HH_ACCESS_TOKEN —
    an application token obtained via client_credentials grant type.
    Without a token HH API returns 403 Forbidden.

    Authorization: Bearer <token> is added automatically when
    access_token is set. If the token is absent — the header is not
    sent (request will likely return 403).
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
        # Treat empty string as "no token"; only fall back to settings when None
        self.access_token = access_token if access_token is not None else settings.hh_access_token
        self.timeout = timeout

    def _headers(self) -> dict[str, str]:
        headers: dict[str, str] = {
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
                status = e.response.status_code
                if status == 403:
                    logger.error(
                        "HH API returned 403 Forbidden — HH_ACCESS_TOKEN is missing or invalid. "
                        "Get a token: python scripts/get_hh_app_token.py"
                    )
                    raise HHClientError(
                        "HH API returned 403 Forbidden. "
                        "Check HH_ACCESS_TOKEN in .env. "
                        "Get a token: python scripts/get_hh_app_token.py"
                    ) from e
                logger.error(f"HH API error {status}: {e.response.text[:200]}")
                raise HHClientError(f"HH API returned {status}") from e
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
        """Search vacancies via HH API. Requires HH_ACCESS_TOKEN.

        HH API params:
            text:       search query (e.g. "Python AI automation")
            area:       region ID (1=Moscow, 2=SPb, 113=Russia)
            salary:     minimum salary
            experience: noExperience | between1And3 | between3And6 | moreThan6
            schedule:   fullDay | shift | flexible | remote | flyInFlyOut
            employment: full | part | project | volunteer | probation
            per_page:   up to 100
            page:       page number (from 0)

        Returns raw HH API JSON: {items, found, pages, page, per_page}.
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
        """Get full vacancy data by ID (including description). Requires HH_ACCESS_TOKEN."""
        return await self._get(f"/vacancies/{vacancy_id}")
