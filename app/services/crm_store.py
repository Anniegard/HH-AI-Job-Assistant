from __future__ import annotations

from dataclasses import dataclass

from app.core.config import settings
from app.core.logging import logger


@dataclass(frozen=True)
class CRMAction:
    chat_id: int
    vacancy_id: str
    action: str


class CRMStore:
    async def get_seen_ids(self, chat_id: int) -> set[str]:
        raise NotImplementedError

    async def save_action(self, action: CRMAction) -> None:
        raise NotImplementedError


class GoogleSheetsCRMStore(CRMStore):
    """Лёгкая обёртка над Google Sheets с graceful fallback при отсутствии зависимостей."""

    def __init__(self) -> None:
        self._enabled = bool(settings.google_sheet_id and settings.google_credentials_path)

    async def get_seen_ids(self, chat_id: int) -> set[str]:
        if not self._enabled:
            return set()
        worksheet = self._open_worksheet()
        if worksheet is None:
            return set()
        records = worksheet.get_all_records()
        return {
            str(row.get("vacancy_id", "")).strip()
            for row in records
            if str(row.get("chat_id", "")).strip() == str(chat_id) and str(row.get("vacancy_id", "")).strip()
        }

    async def save_action(self, action: CRMAction) -> None:
        if not self._enabled:
            return
        worksheet = self._open_worksheet()
        if worksheet is None:
            return
        records = worksheet.get_all_records()
        exists = any(
            str(row.get("chat_id", "")).strip() == str(action.chat_id)
            and str(row.get("vacancy_id", "")).strip() == action.vacancy_id
            for row in records
        )
        if exists:
            return
        worksheet.append_row([str(action.chat_id), action.vacancy_id, action.action], value_input_option="RAW")

    def _open_worksheet(self):
        try:
            import gspread
            from google.oauth2.service_account import Credentials
        except ImportError:
            logger.warning("Google Sheets dependencies are missing; CRM sync disabled.")
            return None

        scopes = ["https://www.googleapis.com/auth/spreadsheets"]
        creds = Credentials.from_service_account_file(settings.google_credentials_path, scopes=scopes)
        gc = gspread.authorize(creds)
        sh = gc.open_by_key(settings.google_sheet_id)
        return sh.sheet1
