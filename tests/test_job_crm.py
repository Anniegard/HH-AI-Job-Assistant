"""Tests for Stage 3.5 — JobCRM and extract_vacancy_id."""

from __future__ import annotations

import pytest

pytest.importorskip("pydantic_settings")

from unittest.mock import MagicMock

from app.services.job_crm import (
    REQUIRED_COLUMNS,
    JobCRM,
    _should_upgrade_status,
    extract_vacancy_id,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _mock_sheets(rows: list[list[str]]) -> MagicMock:
    """Return a SheetsClient mock backed by *rows* (row 0 = header)."""
    sheets = MagicMock()
    sheets.read_all_values.return_value = rows
    sheets.append_row.return_value = None
    sheets.update_row.return_value = None
    sheets.update_header_row.return_value = None
    return sheets


def _crm_with(rows: list[list[str]]) -> JobCRM:
    sheets = _mock_sheets(rows)
    crm = JobCRM(sheets=sheets)
    return crm


def _full_header() -> list[str]:
    return list(REQUIRED_COLUMNS)


def _row(vacancy_id: str, status: str = "new", letter: str = "", notes: str = "") -> list[str]:
    h = _full_header()
    mapping = {
        "date": "2026-01-01T00:00:00+00:00",
        "vacancy_id": vacancy_id,
        "Name": f"Job {vacancy_id}",
        "Company": "ACME",
        "Link": f"https://hh.ru/vacancy/{vacancy_id}",
        "Score": "75",
        "status": status,
        "Tags": "Python",
        "Letter": letter,
        "notes": notes,
        "updated_at": "2026-01-01T00:00:00+00:00",
    }
    return [mapping.get(col, "") for col in h]


# ---------------------------------------------------------------------------
# extract_vacancy_id
# ---------------------------------------------------------------------------


class TestExtractVacancyId:
    def test_extracts_from_hh_url(self):
        assert extract_vacancy_id("https://hh.ru/vacancy/132757934") == "132757934"

    def test_extracts_from_url_with_trailing_slash(self):
        assert extract_vacancy_id("https://hh.ru/vacancy/999/") == "999"

    def test_returns_raw_numeric_id(self):
        assert extract_vacancy_id("12345") == "12345"

    def test_returns_empty_for_non_vacancy_url(self):
        assert extract_vacancy_id("https://hh.ru/employer/123") == ""

    def test_returns_empty_for_empty_string(self):
        assert extract_vacancy_id("") == ""

    def test_returns_empty_for_non_numeric(self):
        assert extract_vacancy_id("not-a-url") == ""


# ---------------------------------------------------------------------------
# _should_upgrade_status
# ---------------------------------------------------------------------------


class TestShouldUpgradeStatus:
    def test_new_to_viewed_is_upgrade(self):
        assert _should_upgrade_status("new", "viewed") is True

    def test_viewed_to_new_is_not_upgrade(self):
        assert _should_upgrade_status("viewed", "new") is False

    def test_saved_to_viewed_is_not_upgrade(self):
        assert _should_upgrade_status("saved", "viewed") is False

    def test_letter_generated_to_saved_is_upgrade(self):
        assert _should_upgrade_status("letter_generated", "saved") is True

    def test_hidden_is_never_overwritten(self):
        assert _should_upgrade_status("hidden", "viewed") is False
        assert _should_upgrade_status("hidden", "saved") is False
        assert _should_upgrade_status("hidden", "interview") is False

    def test_rejected_is_never_overwritten(self):
        assert _should_upgrade_status("rejected", "new") is False

    def test_applied_to_interview_is_upgrade(self):
        assert _should_upgrade_status("applied", "interview") is True

    def test_same_status_is_not_upgrade(self):
        assert _should_upgrade_status("viewed", "viewed") is False


# ---------------------------------------------------------------------------
# JobCRM.upsert_job — create
# ---------------------------------------------------------------------------


class TestUpsertJobCreate:
    def test_appends_new_row_when_unknown(self):
        crm = _crm_with([_full_header()])
        crm.upsert_job({"vacancy_id": "111", "Name": "Dev", "status": "viewed"})
        crm._sheets.append_row.assert_called_once()

    def test_new_row_contains_vacancy_id(self):
        crm = _crm_with([_full_header()])
        crm.upsert_job({"vacancy_id": "222", "Name": "Dev", "status": "new"})
        row = crm._sheets.append_row.call_args[0][0]
        idx = _full_header().index("vacancy_id")
        assert row[idx] == "222"

    def test_new_row_status_is_set(self):
        crm = _crm_with([_full_header()])
        crm.upsert_job({"vacancy_id": "333", "status": "viewed"})
        row = crm._sheets.append_row.call_args[0][0]
        idx = _full_header().index("status")
        assert row[idx] == "viewed"

    def test_no_append_when_vacancy_id_missing(self):
        crm = _crm_with([_full_header()])
        crm.upsert_job({"Name": "Dev", "status": "new"})
        crm._sheets.append_row.assert_not_called()

    def test_cache_updated_after_insert(self):
        crm = _crm_with([_full_header()])
        crm.upsert_job({"vacancy_id": "444", "status": "new"})
        assert crm.is_known("444")


# ---------------------------------------------------------------------------
# JobCRM.upsert_job — update
# ---------------------------------------------------------------------------


class TestUpsertJobUpdate:
    def _crm_with_row(self, vacancy_id: str, status: str = "new", letter: str = "") -> JobCRM:
        rows = [_full_header(), _row(vacancy_id, status=status, letter=letter)]
        return _crm_with(rows)

    def test_updates_existing_row_not_appends(self):
        crm = self._crm_with_row("100")
        crm.upsert_job({"vacancy_id": "100", "status": "viewed"})
        crm._sheets.append_row.assert_not_called()
        crm._sheets.update_row.assert_called_once()

    def test_status_upgraded_from_new_to_viewed(self):
        crm = self._crm_with_row("200", status="new")
        crm.upsert_job({"vacancy_id": "200", "status": "viewed"})
        job = crm.get_job_by_vacancy_id("200")
        assert job["status"] == "viewed"

    def test_status_not_downgraded_from_saved_to_viewed(self):
        crm = self._crm_with_row("300", status="saved")
        crm.upsert_job({"vacancy_id": "300", "status": "viewed"})
        job = crm.get_job_by_vacancy_id("300")
        assert job["status"] == "saved"

    def test_letter_not_overwritten_with_empty(self):
        crm = self._crm_with_row("400", letter="Original letter")
        crm.upsert_job({"vacancy_id": "400", "Letter": "", "status": "viewed"})
        job = crm.get_job_by_vacancy_id("400")
        assert job["Letter"] == "Original letter"

    def test_letter_can_be_updated_with_non_empty(self):
        crm = self._crm_with_row("500", letter="Old")
        crm.upsert_job({"vacancy_id": "500", "Letter": "New letter"})
        job = crm.get_job_by_vacancy_id("500")
        assert job["Letter"] == "New letter"

    def test_notes_not_overwritten_with_empty(self):
        rows = [_full_header(), _row("600", notes="Keep this note")]
        crm = _crm_with(rows)
        crm.upsert_job({"vacancy_id": "600", "notes": ""})
        job = crm.get_job_by_vacancy_id("600")
        assert job["notes"] == "Keep this note"

    def test_hidden_status_not_changed_by_upsert(self):
        crm = self._crm_with_row("700", status="hidden")
        crm.upsert_job({"vacancy_id": "700", "status": "viewed"})
        job = crm.get_job_by_vacancy_id("700")
        assert job["status"] == "hidden"


# ---------------------------------------------------------------------------
# JobCRM.update_status
# ---------------------------------------------------------------------------


class TestUpdateStatus:
    def test_updates_known_vacancy(self):
        rows = [_full_header(), _row("10", status="new")]
        crm = _crm_with(rows)
        result = crm.update_status("10", "saved")
        assert result is True
        assert crm.get_job_by_vacancy_id("10")["status"] == "saved"

    def test_returns_false_for_unknown_vacancy(self):
        crm = _crm_with([_full_header()])
        assert crm.update_status("unknown", "saved") is False

    def test_does_not_downgrade_status(self):
        rows = [_full_header(), _row("20", status="saved")]
        crm = _crm_with(rows)
        result = crm.update_status("20", "viewed")
        # Should return False (not updated) and keep saved
        assert result is False
        assert crm.get_job_by_vacancy_id("20")["status"] == "saved"

    def test_hidden_not_overwritten(self):
        rows = [_full_header(), _row("30", status="hidden")]
        crm = _crm_with(rows)
        crm.update_status("30", "viewed")
        assert crm.get_job_by_vacancy_id("30")["status"] == "hidden"


# ---------------------------------------------------------------------------
# JobCRM.save_letter
# ---------------------------------------------------------------------------


class TestSaveLetter:
    def test_saves_letter_and_upgrades_status(self):
        rows = [_full_header(), _row("50", status="viewed")]
        crm = _crm_with(rows)
        result = crm.save_letter("50", "Dear hiring manager…")
        assert result is True
        job = crm.get_job_by_vacancy_id("50")
        assert job["Letter"] == "Dear hiring manager…"
        assert job["status"] == "letter_generated"

    def test_returns_false_for_unknown_vacancy(self):
        crm = _crm_with([_full_header()])
        assert crm.save_letter("unknown", "letter") is False

    def test_does_not_downgrade_status_to_letter_generated(self):
        rows = [_full_header(), _row("60", status="saved")]
        crm = _crm_with(rows)
        crm.save_letter("60", "My letter")
        # saved > letter_generated → status stays saved
        assert crm.get_job_by_vacancy_id("60")["status"] == "saved"
        # But letter is still saved
        assert crm.get_job_by_vacancy_id("60")["Letter"] == "My letter"


# ---------------------------------------------------------------------------
# JobCRM.should_skip
# ---------------------------------------------------------------------------


class TestShouldSkip:
    @pytest.mark.parametrize("status", ["hidden", "applied", "rejected"])
    def test_skip_statuses(self, status: str):
        rows = [_full_header(), _row("80", status=status)]
        crm = _crm_with(rows)
        assert crm.should_skip("80") is True

    @pytest.mark.parametrize("status", ["new", "viewed", "saved", "letter_generated", "interview"])
    def test_no_skip_statuses(self, status: str):
        rows = [_full_header(), _row("90", status=status)]
        crm = _crm_with(rows)
        assert crm.should_skip("90") is False

    def test_unknown_vacancy_is_not_skipped(self):
        crm = _crm_with([_full_header()])
        assert crm.should_skip("9999") is False


# ---------------------------------------------------------------------------
# JobCRM — backward compatibility: old sheet schema
# ---------------------------------------------------------------------------


class TestBackwardCompatibility:
    def test_missing_columns_are_appended_to_header(self):
        """Sheet without vacancy_id / notes / updated_at should not crash."""
        old_header = ["date", "vacancy", "company", "url", "score", "status", "reason", "cover_letter"]
        data_row = ["2025-01-01", "Dev", "ACME", "https://hh.ru/vacancy/1", "80", "viewed", "r", ""]
        crm = _crm_with([old_header, data_row])
        # Should call update_header_row with the extended headers
        crm._ensure_loaded()
        crm._sheets.update_header_row.assert_called_once()
        new_headers = crm._sheets.update_header_row.call_args[0][0]
        for col in REQUIRED_COLUMNS:
            assert col in new_headers

    def test_is_known_does_not_crash_on_old_schema(self):
        old_header = ["date", "vacancy", "company", "url", "score", "status"]
        crm = _crm_with([old_header])
        assert crm.is_known("does-not-exist") is False

    def test_empty_sheet_initialises_clean(self):
        crm = _crm_with([])
        crm._ensure_loaded()
        crm._sheets.update_header_row.assert_called_once_with(REQUIRED_COLUMNS)
        assert crm._cache == []


# ---------------------------------------------------------------------------
# JobCRM.load_jobs
# ---------------------------------------------------------------------------


class TestLoadJobs:
    def test_returns_list_of_dicts(self):
        rows = [_full_header(), _row("X1"), _row("X2")]
        crm = _crm_with(rows)
        jobs = crm.load_jobs()
        assert len(jobs) == 2
        assert jobs[0]["vacancy_id"] == "X1"
        assert jobs[1]["vacancy_id"] == "X2"

    def test_load_jobs_forces_refresh(self):
        rows = [_full_header(), _row("R1")]
        crm = _crm_with(rows)
        # Populate cache
        crm.load_jobs()
        # Change what the mock returns and reload
        crm._sheets.read_all_values.return_value = [_full_header(), _row("R2")]
        jobs = crm.load_jobs()
        assert jobs[0]["vacancy_id"] == "R2"
