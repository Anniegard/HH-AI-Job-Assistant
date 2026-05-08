"""Тест HH клиента — мок httpx."""

from __future__ import annotations

import httpx
import pytest

from app.services.hh_client import HHClient, HHClientError


@pytest.mark.asyncio
async def test_search_vacancies_builds_params(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict = {}

    class MockResponse:
        status_code = 200

        def raise_for_status(self) -> None:
            pass

        def json(self) -> dict:
            return {"items": [], "found": 0, "pages": 0, "page": 0, "per_page": 10}

    class MockAsyncClient:
        def __init__(self, *args, **kwargs) -> None:
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            pass

        async def get(self, url, params=None, headers=None):
            captured["url"] = url
            captured["params"] = params
            captured["headers"] = headers
            return MockResponse()

    monkeypatch.setattr(httpx, "AsyncClient", MockAsyncClient)

    client = HHClient()
    result = await client.search_vacancies(
        text="Python", area=1, salary=150000, schedule="remote", per_page=10
    )

    assert captured["url"].endswith("/vacancies")
    assert captured["params"]["text"] == "Python"
    assert captured["params"]["area"] == 1
    assert captured["params"]["salary"] == 150000
    assert captured["params"]["schedule"] == "remote"
    assert captured["params"]["per_page"] == 10
    assert "User-Agent" in captured["headers"]
    assert result["found"] == 0


@pytest.mark.asyncio
async def test_search_raises_on_http_error(monkeypatch: pytest.MonkeyPatch) -> None:
    class MockResponse:
        status_code = 403
        text = "forbidden"

        def raise_for_status(self) -> None:
            raise httpx.HTTPStatusError(
                "403", request=httpx.Request("GET", "https://x"), response=self  # type: ignore[arg-type]
            )

    class MockAsyncClient:
        def __init__(self, *args, **kwargs) -> None:
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            pass

        async def get(self, *args, **kwargs):
            return MockResponse()

    monkeypatch.setattr(httpx, "AsyncClient", MockAsyncClient)

    client = HHClient()
    with pytest.raises(HHClientError):
        await client.search_vacancies(text="x")
