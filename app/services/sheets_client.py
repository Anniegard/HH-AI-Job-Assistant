from __future__ import annotations

from typing import Any

from app.core.config import settings
from app.core.logging import logger

try:
    from googleapiclient.errors import HttpError as _GoogleHttpError
except ImportError:
    _GoogleHttpError = Exception  # type: ignore[assignment,misc]


def _col_letter(n: int) -> str:
    """Convert 0-indexed column number to A1 column letter (A, B, ..., Z, AA, ...)."""
    result = ""
    while True:
        result = chr(ord("A") + n % 26) + result
        n = n // 26 - 1
        if n < 0:
            break
    return result


class SheetsClientError(RuntimeError):
    pass


class SheetsClient:
    def __init__(self, service=None, sheet_id=None, sheet_name=None):
        self.sheet_id = sheet_id or settings.google_sheet_id
        self.sheet_name = sheet_name or settings.google_sheet_name
        self._service = service

    def _get_service(self):
        if self._service is not None:
            return self._service
        try:
            from google.oauth2.service_account import Credentials
            from googleapiclient.discovery import build
        except ImportError as e:
            raise SheetsClientError("Google API dependencies are not installed") from e

        scopes = ["https://www.googleapis.com/auth/spreadsheets"]
        creds = Credentials.from_service_account_file(settings.google_credentials_path, scopes=scopes)
        self._service = build("sheets", "v4", credentials=creds)
        return self._service

    @property
    def _sheet(self) -> str:
        """Sheet name quoted for use in A1 range notation (handles spaces/dots/hyphens)."""
        return f"'{self.sheet_name}'"

    @property
    def _values(self):
        return self._get_service().spreadsheets().values()

    def _exec(self, request) -> Any:
        """Execute a Google API request, converting HttpError to SheetsClientError."""
        try:
            return request.execute()
        except _GoogleHttpError as e:
            raise SheetsClientError(f"Google Sheets API error: {e}") from e

    def append_vacancy(self, row: list[Any]) -> None:
        self._exec(self._values.append(
            spreadsheetId=self.sheet_id,
            range=f"{self._sheet}!A:H",
            valueInputOption="RAW",
            insertDataOption="INSERT_ROWS",
            body={"values": [row]},
        ))

    def update_status(self, vacancy_url: str, status: str) -> bool:
        rows = self._exec(
            self._values.get(spreadsheetId=self.sheet_id, range=f"{self._sheet}!A:G")
        ).get("values", [])
        for idx, row in enumerate(rows[1:], start=2):
            if len(row) >= 4 and row[3] == vacancy_url:
                self._exec(self._values.update(
                    spreadsheetId=self.sheet_id,
                    range=f"{self._sheet}!F{idx}",
                    valueInputOption="RAW",
                    body={"values": [[status]]},
                ))
                return True
        logger.info("Vacancy url not found in sheet for status update: %s", vacancy_url)
        return False

    def update_cover_letter(self, vacancy_url: str, cover_letter: str) -> bool:
        rows = self._exec(
            self._values.get(spreadsheetId=self.sheet_id, range=f"{self._sheet}!A:H")
        ).get("values", [])
        for idx, row in enumerate(rows[1:], start=2):
            if len(row) >= 4 and row[3] == vacancy_url:
                self._exec(self._values.update(
                    spreadsheetId=self.sheet_id,
                    range=f"{self._sheet}!H{idx}",
                    valueInputOption="RAW",
                    body={"values": [[cover_letter]]},
                ))
                return True
        logger.info("Vacancy url not found in sheet for cover letter update: %s", vacancy_url)
        return False

    def list_seen_urls(self) -> set[str]:
        rows = self._exec(
            self._values.get(spreadsheetId=self.sheet_id, range=f"{self._sheet}!D:D")
        ).get("values", [])
        return {r[0] for r in rows[1:] if r and r[0]}

    def list_seen_ids(self) -> set[str]:
        return self.list_seen_urls()

    # ------------------------------------------------------------------
    # Low-level primitives for JobCRM (Stage 3.5)
    # ------------------------------------------------------------------

    def read_all_values(self) -> list[list[str]]:
        """Read the entire sheet as a 2-D list of strings (row 0 = headers)."""
        raw = self._exec(
            self._values.get(spreadsheetId=self.sheet_id, range=f"{self._sheet}!A:ZZ")
        ).get("values", [])
        return [[str(cell) for cell in row] for row in raw]

    def update_header_row(self, headers: list[str]) -> None:
        """Overwrite row 1 (the header row) with *headers*."""
        end = _col_letter(len(headers) - 1)
        self._exec(self._values.update(
            spreadsheetId=self.sheet_id,
            range=f"{self._sheet}!A1:{end}1",
            valueInputOption="RAW",
            body={"values": [headers]},
        ))

    def update_row(self, row_idx: int, values: list[Any]) -> None:
        """Overwrite a full row at 1-based *row_idx* with *values*."""
        end = _col_letter(len(values) - 1)
        self._exec(self._values.update(
            spreadsheetId=self.sheet_id,
            range=f"{self._sheet}!A{row_idx}:{end}{row_idx}",
            valueInputOption="RAW",
            body={"values": [values]},
        ))

    def append_row(self, values: list[Any]) -> None:
        """Append a single data row after the last populated row."""
        self._exec(self._values.append(
            spreadsheetId=self.sheet_id,
            range=f"{self._sheet}!A:A",
            valueInputOption="RAW",
            insertDataOption="INSERT_ROWS",
            body={"values": [values]},
        ))
