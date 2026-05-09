"""Stage 3.5 — Google Sheets as persistent job CRM.

JobCRM sits on top of SheetsClient and treats the sheet as a key-value
store keyed by *vacancy_id*.  All reads are served from an in-memory
cache loaded once per session; writes go directly to the sheet and also
update the cache so subsequent calls stay consistent without a re-read.

Column schema (REQUIRED_COLUMNS):
    date · vacancy_id · Name · Company · Link · Score · status
    · Tags · Letter · notes · updated_at

Existing sheets that lack some columns are extended automatically on
first access (the missing columns are appended to the header row).

Status priority (lowest → highest):
    new → viewed → letter_generated → saved → applied → interview

``hidden`` and ``rejected`` are manual final statuses: they are never
overwritten by automatic bot actions.
"""

from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import TYPE_CHECKING

from app.core.logging import logger

if TYPE_CHECKING:
    from app.services.sheets_client import SheetsClient

# ---------------------------------------------------------------------------
# Schema
# ---------------------------------------------------------------------------

REQUIRED_COLUMNS: list[str] = [
    "date",
    "vacancy_id",
    "Name",
    "Company",
    "Link",
    "Score",
    "status",
    "Tags",
    "Letter",
    "notes",
    "updated_at",
]

# Statuses that should cause a vacancy to be skipped (not shown to user)
SKIP_STATUSES: frozenset[str] = frozenset({"hidden", "applied", "rejected"})

# Manual final statuses — never changed by automatic bot actions
_MANUAL_FINAL: frozenset[str] = frozenset({"hidden", "rejected"})

# Priority order for upgradeable statuses (higher number = higher priority)
STATUS_PRIORITY: dict[str, int] = {
    "new": 0,
    "viewed": 1,
    "letter_generated": 2,
    "saved": 3,
    "applied": 4,
    "interview": 5,
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def extract_vacancy_id(link: str) -> str:
    """Extract the numeric vacancy ID from an HH URL.

    Handles both ``https://hh.ru/vacancy/132757934`` and plain IDs.

    Returns the ID as a string, or ``""`` if not found.
    """
    if not link:
        return ""
    m = re.search(r"/vacancy/(\d+)", link)
    if m:
        return m.group(1)
    # Maybe the caller passed a raw numeric id already
    if re.fullmatch(r"\d+", link.strip()):
        return link.strip()
    return ""


def _should_upgrade_status(current: str, new: str) -> bool:
    """Return True if *new* status should replace *current*.

    Rules:
    - Manual final statuses (``hidden``, ``rejected``) are never changed.
    - For statuses in STATUS_PRIORITY, only upgrade (new priority > current).
    - Unknown statuses are always replaceable.
    """
    if current in _MANUAL_FINAL:
        return False
    cur_p = STATUS_PRIORITY.get(current, -1)
    new_p = STATUS_PRIORITY.get(new, -1)
    if cur_p >= 0 and new_p >= 0:
        return new_p > cur_p
    # Current is unknown / not in priority table → allow update
    return True


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


# ---------------------------------------------------------------------------
# JobCRM
# ---------------------------------------------------------------------------


class JobCRM:
    """High-level CRM service backed by a Google Sheet.

    The cache is a list of ``(sheet_row_index, job_dict)`` tuples where
    ``sheet_row_index`` is 1-based (row 1 = header, row 2 = first data row).
    """

    def __init__(self, sheets: SheetsClient | None = None) -> None:
        if sheets is None:
            from app.services.sheets_client import SheetsClient

            sheets = SheetsClient()
        self._sheets = sheets
        self._headers: list[str] | None = None
        # List of (1-based sheet row index, job dict)
        self._cache: list[tuple[int, dict[str, str]]] | None = None

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _load(self) -> None:
        """Read the sheet and populate *_headers* and *_cache*."""
        all_rows = self._sheets.read_all_values()
        if not all_rows:
            # Empty sheet — write the header row and initialise empty cache
            self._sheets.update_header_row(REQUIRED_COLUMNS)
            self._headers = list(REQUIRED_COLUMNS)
            self._cache = []
            return

        headers = all_rows[0]

        # Ensure required columns are present
        missing = [c for c in REQUIRED_COLUMNS if c not in headers]
        if missing:
            headers = headers + missing
            self._sheets.update_header_row(headers)

        self._headers = headers
        self._cache = []
        for sheet_row_idx, row in enumerate(all_rows[1:], start=2):
            # Pad short rows to header length
            padded = list(row) + [""] * (len(headers) - len(row))
            self._cache.append((sheet_row_idx, dict(zip(headers, padded, strict=False))))

    def _ensure_loaded(self) -> None:
        if self._cache is None:
            self._load()

    def _headers_safe(self) -> list[str]:
        self._ensure_loaded()
        return self._headers  # type: ignore[return-value]

    def _find(self, vacancy_id: str) -> tuple[int, dict[str, str]] | None:
        """Return ``(sheet_row_idx, job_dict)`` for *vacancy_id*, or None."""
        self._ensure_loaded()
        for row_idx, job in self._cache:  # type: ignore[union-attr]
            if job.get("vacancy_id") == vacancy_id:
                return row_idx, job
        return None

    def _build_row(self, job: dict[str, str], headers: list[str]) -> list[str]:
        return [job.get(col, "") for col in headers]

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def load_jobs(self) -> list[dict[str, str]]:
        """Force a full re-read from the sheet and return all jobs."""
        self._cache = None
        self._headers = None
        self._load()
        return [job for _, job in self._cache]  # type: ignore[union-attr]

    def get_job_by_vacancy_id(self, vacancy_id: str) -> dict[str, str] | None:
        """Return the job dict for *vacancy_id*, or ``None`` if not found."""
        result = self._find(vacancy_id)
        return result[1] if result else None

    def is_known(self, vacancy_id: str) -> bool:
        """Return True if *vacancy_id* already exists in the sheet."""
        return self._find(vacancy_id) is not None

    def should_skip(self, vacancy_id: str) -> bool:
        """Return True if the vacancy should be hidden from the user.

        Skips vacancies with status in ``SKIP_STATUSES``.
        Unknown vacancy IDs are *not* skipped.
        """
        job = self.get_job_by_vacancy_id(vacancy_id)
        if job is None:
            return False
        return job.get("status", "") in SKIP_STATUSES

    def upsert_job(self, job: dict[str, str]) -> None:
        """Insert or update a job row keyed by ``vacancy_id``.

        Merge rules:
        - ``Letter`` is never overwritten with an empty value.
        - ``notes`` is never overwritten with an empty value.
        - ``status`` is only upgraded (see STATUS_PRIORITY); manual final
          statuses (``hidden``, ``rejected``) are never touched.
        - ``updated_at`` is always set to the current UTC timestamp.
        """
        vacancy_id = job.get("vacancy_id", "").strip()
        if not vacancy_id:
            logger.warning("upsert_job called without vacancy_id — skipping")
            return

        headers = self._headers_safe()
        now = _now_iso()
        existing = self._find(vacancy_id)

        if existing is None:
            # ---- New row ----
            new_job: dict[str, str] = {col: "" for col in headers}
            new_job["date"] = now
            new_job["updated_at"] = now
            # Apply provided values (only columns that exist in headers)
            for col, val in job.items():
                if col in new_job:
                    new_job[col] = val
            row = self._build_row(new_job, headers)
            self._sheets.append_row(row)
            # Next data row index = header(1) + len(existing cache) + 1 (new row)
            new_idx = len(self._cache) + 2  # type: ignore[arg-type]
            self._cache.append((new_idx, new_job))  # type: ignore[union-attr]
            logger.info("JobCRM: added vacancy %s", vacancy_id)
        else:
            # ---- Update existing row ----
            row_idx, cached = existing
            updates: dict[str, str] = {"updated_at": now}

            for col, val in job.items():
                if col not in headers:
                    continue
                # Protect important fields from being blanked
                if col in ("Letter", "notes") and not val:
                    continue
                if col == "status":
                    current_status = cached.get("status", "")
                    if not _should_upgrade_status(current_status, val):
                        continue
                # Only write if value is non-empty OR we're explicitly clearing
                # a non-protected field (e.g., Tags reset)
                updates[col] = val

            cached.update(updates)
            row = self._build_row(cached, headers)
            self._sheets.update_row(row_idx, row)
            logger.info("JobCRM: updated vacancy %s", vacancy_id)

    def update_status(self, vacancy_id: str, status: str) -> bool:
        """Update only the ``status`` field for *vacancy_id*.

        Returns True if the row was found and updated.
        """
        self._ensure_loaded()
        existing = self._find(vacancy_id)
        if existing is None:
            logger.info("JobCRM.update_status: vacancy %s not found", vacancy_id)
            return False
        row_idx, cached = existing
        current = cached.get("status", "")
        if not _should_upgrade_status(current, status):
            logger.info(
                "JobCRM.update_status: skipping downgrade %s → %s for %s",
                current, status, vacancy_id,
            )
            return False
        cached["status"] = status
        cached["updated_at"] = _now_iso()
        row = self._build_row(cached, self._headers_safe())
        self._sheets.update_row(row_idx, row)
        return True

    def save_letter(self, vacancy_id: str, letter: str) -> bool:
        """Save a cover letter and set status to ``letter_generated``.

        Returns True if the row was found and updated.
        """
        self._ensure_loaded()
        existing = self._find(vacancy_id)
        if existing is None:
            logger.info("JobCRM.save_letter: vacancy %s not found", vacancy_id)
            return False
        row_idx, cached = existing
        now = _now_iso()
        cached["Letter"] = letter
        cached["updated_at"] = now
        # Upgrade status to letter_generated if possible
        current_status = cached.get("status", "")
        if _should_upgrade_status(current_status, "letter_generated"):
            cached["status"] = "letter_generated"
        row = self._build_row(cached, self._headers_safe())
        self._sheets.update_row(row_idx, row)
        return True
