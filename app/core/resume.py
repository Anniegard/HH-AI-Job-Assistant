"""Resume context loader for cover letter generation."""

from __future__ import annotations

from app.core.config import settings
from app.core.logging import logger


def load_resume_context(max_chars: int = 6000) -> str:
    """Load resume markdown and return it as a string.

    Falls back to ``settings.user_profile`` if the file is missing,
    empty, or unreadable.  Never raises.

    Args:
        max_chars: Maximum number of characters to return.  Longer
            content is silently truncated.

    Returns:
        Resume text (up to *max_chars* characters).
    """
    path = settings.resume_md_path
    try:
        with open(path, encoding="utf-8") as fh:
            content = fh.read().strip()
        if not content:
            logger.warning("resume.md is empty (%s), falling back to user_profile", path)
            return settings.user_profile[:max_chars]
        return content[:max_chars]
    except FileNotFoundError:
        logger.warning("resume.md not found at '%s', falling back to user_profile", path)
        return settings.user_profile[:max_chars]
    except OSError as exc:
        logger.warning("Cannot read resume.md ('%s'): %s — falling back to user_profile", path, exc)
        return settings.user_profile[:max_chars]
