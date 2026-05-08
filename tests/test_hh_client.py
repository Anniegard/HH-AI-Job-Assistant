"""Test HH client using httpx mocks. No real network calls."""

from __future__ import annotations

import pytest

httpx = pytest.importorskip("httpx")

from app.services.hh_client import HHClient, HHClientError


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_ok_client(captured: dict):
    """Returns MockAsyncClient that records the GET call into 'captured'."""

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

    return MockAsyncClient


def _make_error_client(http_status: int):
    """Returns MockAsyncClient that always raises HTTPStatusError with given status.

    Note: Python class bodies don't form closures over enclosing function scopes,
    so we use a plain int attribute value directly, not a name alias.
    """

    class MockAsyncClient:
        def __init__(self, *args, **kwargs) -> None:
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            pass

        async def get(self, *args, **kwargs):
            # Build a minimal response-like object inline to avoid scoping issue
            class _Resp:
                text = "error body"

            resp = _Resp()
            resp.status_code = http_status  # set on instance, not class — no scoping issue
            raise httpx.HTTPStatusError(
                str(http_status),
                request=httpx.Request("GET", "https://api.hh.ru/vacancies"),
                response=resp,  # type: ignore[arg-type]
            )

    return MockAsyncClient


# ---------------------------------------------------------------------------
# Search params
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_search_vacancies_builds_params(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict = {}
    monkeypatch.setattr(httpx, "AsyncClient", _make_ok_client(captured))

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


# ---------------------------------------------------------------------------
# Authorization header present when token is given
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_authorization_header_sent_when_token_given(monkeypatch: pytest.MonkeyPatch) -> None:
    """Authorization: Bearer must be present when access_token is explicitly set."""
    captured: dict = {}
    monkeypatch.setattr(httpx, "AsyncClient", _make_ok_client(captured))

    client = HHClient(access_token="test-secret-token")
    await client.search_vacancies(text="Python")

    assert "Authorization" in captured["headers"]
    assert captured["headers"]["Authorization"] == "Bearer test-secret-token"


# ---------------------------------------------------------------------------
# Authorization header absent when no token
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_authorization_header_absent_when_no_token(monkeypatch: pytest.MonkeyPatch) -> None:
    """Authorization must NOT be sent when access_token is explicitly empty string.

    We also clear settings.hh_access_token to isolate from any real .env values.
    """
    captured: dict = {}
    monkeypatch.setattr(httpx, "AsyncClient", _make_ok_client(captured))

    # Isolate from real .env — in case HH_ACCESS_TOKEN is set locally
    import app.services.hh_client as hh_mod
    monkeypatch.setattr(hh_mod.settings, "hh_access_token", "")

    client = HHClient(access_token="")
    await client.search_vacancies(text="Python")

    assert "Authorization" not in captured["headers"]


# ---------------------------------------------------------------------------
# 403 raises HHClientError with a hint about HH_ACCESS_TOKEN
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_403_raises_hh_client_error_with_hint(monkeypatch: pytest.MonkeyPatch) -> None:
    """On 403, HHClientError message must mention HH_ACCESS_TOKEN."""
    monkeypatch.setattr(httpx, "AsyncClient", _make_error_client(403))

    client = HHClient(access_token="bad-token")
    with pytest.raises(HHClientError) as exc_info:
        await client.search_vacancies(text="Python")

    error_msg = str(exc_info.value)
    assert "403" in error_msg
    assert "HH_ACCESS_TOKEN" in error_msg


# ---------------------------------------------------------------------------
# Non-403 HTTP errors still raise HHClientError
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_non_403_http_error_raises_hh_client_error(monkeypatch: pytest.MonkeyPatch) -> None:
    """On 500, HHClientError must be raised."""
    monkeypatch.setattr(httpx, "AsyncClient", _make_error_client(500))

    client = HHClient(access_token="some-token")
    with pytest.raises(HHClientError) as exc_info:
        await client.search_vacancies(text="x")

    assert "500" in str(exc_info.value)
