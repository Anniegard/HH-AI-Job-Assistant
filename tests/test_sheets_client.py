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


def test_append_vacancy_calls_api():
    service, values = _mock_service([[]])
    client = SheetsClient(service=service, sheet_id="sid", sheet_name="CRM")
    client.append_vacancy(["d", "v", "c", "u", "90", "viewed", "reason", ""])
    values.append.assert_called_once()


def test_update_status_updates_matching_row():
    service, values = _mock_service([
        ["date", "vacancy", "company", "url", "score", "status", "reason"],
        ["d", "v", "c", "https://x", "80", "viewed", "r"],
    ])
    client = SheetsClient(service=service, sheet_id="sid", sheet_name="CRM")
    updated = client.update_status("https://x", "saved")
    assert updated is True
    values.update.assert_called_once()


def test_list_seen_ids_reads_url_column():
    service, _ = _mock_service([["url"], ["https://a"], ["https://b"]])
    client = SheetsClient(service=service, sheet_id="sid", sheet_name="CRM")
    seen = client.list_seen_ids()
    assert seen == {"https://a", "https://b"}


def test_list_seen_urls_reads_url_column():
    service, _ = _mock_service([["url"], ["https://a"], ["https://b"]])
    client = SheetsClient(service=service, sheet_id="sid", sheet_name="CRM")
    seen = client.list_seen_urls()
    assert seen == {"https://a", "https://b"}


def test_update_cover_letter_updates_matching_row():
    service, values = _mock_service([
        ["date", "vacancy", "company", "url", "score", "status", "reason", "cover_letter"],
        ["d", "v", "c", "https://hh.ru/v/1", "80", "viewed", "r", ""],
    ])
    client = SheetsClient(service=service, sheet_id="sid", sheet_name="CRM")

    updated = client.update_cover_letter("https://hh.ru/v/1", "Hello!")

    assert updated is True
    values.update.assert_called_once()
    call_body = values.update.call_args[1]["body"]
    assert call_body["values"] == [["Hello!"]]


def test_update_cover_letter_returns_false_if_not_found():
    service, values = _mock_service([
        ["date", "vacancy", "company", "url", "score", "status", "reason", "cover_letter"],
        ["d", "v", "c", "https://other.url", "80", "viewed", "r", ""],
    ])
    client = SheetsClient(service=service, sheet_id="sid", sheet_name="CRM")

    updated = client.update_cover_letter("https://hh.ru/v/missing", "Letter")

    assert updated is False
    values.update.assert_not_called()
