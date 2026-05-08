import pytest
pytest.importorskip("pydantic_settings")

from unittest.mock import MagicMock

from app.services.sheets_client import SheetsClient


def _mock_service(rows):
    service = MagicMock()
    values = service.spreadsheets.return_value.values.return_value
    values.get.return_value.execute.return_value = {"values": rows}
    values.append.return_value.execute.return_value = {}
    values.update.return_value.execute.return_value = {}
    return service, values


def test_append_vacancy_calls_api() -> None:
    service, values = _mock_service([[]])
    client = SheetsClient(service=service, sheet_id="sid", sheet_name="CRM")

    client.append_vacancy(["d", "v", "c", "u", "90", "viewed", "reason", "", "", "2026-01-01"])

    values.append.assert_called_once()


def test_update_status_updates_matching_row() -> None:
    service, values = _mock_service([
        ["date", "vacancy", "company", "url", "score", "status", "reason", "cover_letter", "response", "published_at"],
        ["d", "v", "c", "https://x", "80", "viewed", "r", "", "", ""],
    ])
    client = SheetsClient(service=service, sheet_id="sid", sheet_name="CRM")

    updated = client.update_status("https://x", "saved")

    assert updated is True
    values.update.assert_called_once()


def test_update_cover_letter_updates_matching_row() -> None:
    service, values = _mock_service([
        ["date", "vacancy", "company", "url", "score", "status", "reason", "cover_letter", "response", "published_at"],
        ["d", "v", "c", "https://x", "80", "viewed", "r", "", "", ""],
    ])
    client = SheetsClient(service=service, sheet_id="sid", sheet_name="CRM")

    updated = client.update_cover_letter("https://x", "hello")

    assert updated is True
    values.update.assert_called_once()


def test_list_seen_urls_reads_url_column() -> None:
    service, _ = _mock_service([
        ["url"],
        ["https://a"],
        ["https://b"],
    ])
    client = SheetsClient(service=service, sheet_id="sid", sheet_name="CRM")

    seen = client.list_seen_urls()

    assert seen == {"https://a", "https://b"}
