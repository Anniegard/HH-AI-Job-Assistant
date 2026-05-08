"""Tests for app.core.resume.load_resume_context."""

from __future__ import annotations

import textwrap
from pathlib import Path
from unittest.mock import patch

from app.core.resume import load_resume_context

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_SAMPLE_RESUME = textwrap.dedent(
    """\
    # Профиль кандидата

    ## Стек
    Python, FastAPI, Telegram bots

    ## Проекты
    - bot-mont-shk: автоматизация Wildberries
    """
)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_reads_resume_file(tmp_path: Path) -> None:
    """load_resume_context() returns content of the resume file."""
    resume_file = tmp_path / "resume.md"
    resume_file.write_text(_SAMPLE_RESUME, encoding="utf-8")

    with patch("app.core.resume.settings") as mock_settings:
        mock_settings.resume_md_path = str(resume_file)
        mock_settings.user_profile = "fallback profile"
        result = load_resume_context()

    assert "bot-mont-shk" in result
    assert "Python" in result


def test_fallback_when_file_missing() -> None:
    """load_resume_context() falls back to user_profile if file doesn't exist."""
    with patch("app.core.resume.settings") as mock_settings:
        mock_settings.resume_md_path = "/nonexistent/path/resume.md"
        mock_settings.user_profile = "fallback profile text"
        result = load_resume_context()

    assert result == "fallback profile text"


def test_fallback_when_file_empty(tmp_path: Path) -> None:
    """load_resume_context() falls back to user_profile if file is empty."""
    resume_file = tmp_path / "resume.md"
    resume_file.write_text("   \n  ", encoding="utf-8")  # only whitespace

    with patch("app.core.resume.settings") as mock_settings:
        mock_settings.resume_md_path = str(resume_file)
        mock_settings.user_profile = "fallback when empty"
        result = load_resume_context()

    assert result == "fallback when empty"


def test_truncates_to_max_chars(tmp_path: Path) -> None:
    """load_resume_context() truncates content to max_chars."""
    resume_file = tmp_path / "resume.md"
    resume_file.write_text("A" * 10_000, encoding="utf-8")

    with patch("app.core.resume.settings") as mock_settings:
        mock_settings.resume_md_path = str(resume_file)
        mock_settings.user_profile = "fallback"
        result = load_resume_context(max_chars=100)

    assert len(result) == 100
    assert result == "A" * 100


def test_fallback_also_truncated() -> None:
    """Fallback user_profile is also subject to max_chars limit."""
    long_profile = "B" * 500

    with patch("app.core.resume.settings") as mock_settings:
        mock_settings.resume_md_path = "/no/such/file.md"
        mock_settings.user_profile = long_profile
        result = load_resume_context(max_chars=50)

    assert len(result) == 50


def test_does_not_raise_on_os_error(tmp_path: Path) -> None:
    """load_resume_context() never raises — returns fallback on any OSError."""
    resume_file = tmp_path / "resume.md"
    resume_file.write_text("content", encoding="utf-8")

    with (
        patch("app.core.resume.settings") as mock_settings,
        patch("builtins.open", side_effect=OSError("permission denied")),
    ):
        mock_settings.resume_md_path = str(resume_file)
        mock_settings.user_profile = "safe fallback"
        result = load_resume_context()

    assert result == "safe fallback"
