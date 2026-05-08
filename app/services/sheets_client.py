from __future__ import annotations

from typing import Any

from app.core.config import settings
from app.core.logging import logger


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
    def _values(self):
        return self._get_service().spreadsheets().values()

    def append_vacancy(self, row: list) -> None:
        self._values.append(
            spreadsheetId=self.sheet_id,
            range=f"{self.sheet_name}!A:H",
            valueInputOption="RAW",
            insertDataOption="INSERT_ROWS",
            body={"values": [row]},
        ).execute()

    def update_status(self, vacancy_url: str, status: str) -> bool:
        rows = self._values.get(spreadsheetId=self.sheet_id, range=f"{self.sheet_name}!A:G").execute().get("values", [])
        for idx, row in enumerate(rows[1:], start=2):
            if len(row) >= 4 and row[3] == vacancy_url:
                self._values.update(
                    spreadsheetId=self.sheet_id,
                    range=f"{self.sheet_name}!F{idx}",
                    valueInputOption="RAW",
                    body={"values": [[status]]},
                ).execute()
                return True
        logger.info("Vacancy url not found in sheet for status update: %s", vacancy_url)
        return False

    def update_cover_letter(self, vacancy_url: str, cover_letter: str) -> bool:
        rows = self._values.get(spreadsheetId=self.sheet_id, range=f"{self.sheet_name}!A:H").execute().get("values", [])
        for idx, row in enumerate(rows[1:], start=2):
            if len(row) >= 4 and row[3] == vacancy_url:
                self._values.update(
                    spreadsheetId=self.sheet_id,
                    range=f"{self.sheet_name}!H{idx}",
                    valueInputOption="RAW",
                    body={"values": [[cover_letter]]},
                ).execute()
                return True
        logger.info("Vacancy url not found in sheet for cover letter update: %s", vacancy_url)
        return False

    def list_seen_urls(self) -> set:
        rows = self._values.get(spreadsheetId=self.sheet_id, range=f"{self.sheet_name}!D:D").execute().get("values", [])
        return {r[0] for r in rows[1:] if r and r[0]}

    def list_seen_ids(self) -> set:
        return self.list_seen_urls()
