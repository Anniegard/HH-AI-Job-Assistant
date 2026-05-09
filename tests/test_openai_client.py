"""Tests for OpenAI client - no real API calls."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from app.services.openai_client import OpenAIClient, OpenAIClientError, build_coverletter_prompt


def _mock_completion(text):
    choice = MagicMock()
    choice.message.content = text
    response = MagicMock()
    response.choices = [choice]
    return response


def test_generate_cover_letter_returns_text():
    client = OpenAIClient(api_key="test-key")
    fake_response = _mock_completion("Dear hiring manager, I want to apply.")

    with patch("app.services.openai_client.OpenAI") as MockOpenAI:
        MockOpenAI.return_value.chat.completions.create.return_value = fake_response
        result = client.generate_cover_letter(vacancy_title="Python Dev", company="ACME")

    assert result == "Dear hiring manager, I want to apply."


def test_generate_cover_letter_strips_whitespace():
    client = OpenAIClient(api_key="test-key")
    fake_response = _mock_completion("  Letter with spaces  ")

    with patch("app.services.openai_client.OpenAI") as MockOpenAI:
        MockOpenAI.return_value.chat.completions.create.return_value = fake_response
        result = client.generate_cover_letter(vacancy_title="Dev", company="Co")

    assert result == "Letter with spaces"


def test_generate_cover_letter_raises_if_no_api_key():
    client = OpenAIClient(api_key="")

    with pytest.raises(OpenAIClientError, match="OPENAI_API_KEY"):
        client.generate_cover_letter(vacancy_title="Dev", company="Co")


def test_generate_cover_letter_raises_on_empty_response():
    client = OpenAIClient(api_key="test-key")
    fake_response = _mock_completion("")

    with patch("app.services.openai_client.OpenAI") as MockOpenAI:
        MockOpenAI.return_value.chat.completions.create.return_value = fake_response
        with pytest.raises(OpenAIClientError, match="empty"):
            client.generate_cover_letter(vacancy_title="Dev", company="Co")


def test_generate_cover_letter_wraps_api_exception():
    client = OpenAIClient(api_key="test-key")

    with patch("app.services.openai_client.OpenAI") as MockOpenAI:
        MockOpenAI.return_value.chat.completions.create.side_effect = RuntimeError("network error")
        with pytest.raises(OpenAIClientError, match="OpenAI API"):
            client.generate_cover_letter(vacancy_title="Dev", company="Co")


def test_generate_cover_letter_includes_vacancy_in_prompt():
    client = OpenAIClient(api_key="test-key")
    fake_response = _mock_completion("Letter")

    with patch("app.services.openai_client.OpenAI") as MockOpenAI:
        mock_create = MockOpenAI.return_value.chat.completions.create
        mock_create.return_value = fake_response

        client.generate_cover_letter(
            vacancy_title="ML Engineer",
            company="DeepMind",
            requirements="PyTorch, transformers",
            user_profile="ML engineer with 5 years exp",
        )

        call_kwargs = mock_create.call_args[1]
        messages = call_kwargs["messages"]
        prompt_text = messages[0]["content"]

    assert "ML Engineer" in prompt_text
    assert "DeepMind" in prompt_text
    assert "PyTorch, transformers" in prompt_text
    assert "ML engineer with 5 years exp" in prompt_text


# ---------------------------------------------------------------------------
# Tests for build_coverletter_prompt()
# ---------------------------------------------------------------------------


def test_prompt_contains_resume_context():
    """Prompt must include the resume/profile text."""
    prompt = build_coverletter_prompt(
        vacancy_title="Python Dev",
        company="ACME",
        requirements="FastAPI",
        resume_context="bot-mont-shk, Wildberries automation",
    )
    assert "bot-mont-shk" in prompt
    assert "Wildberries automation" in prompt


def test_prompt_contains_vacancy_and_company():
    """Prompt must mention both vacancy title and company."""
    prompt = build_coverletter_prompt(
        vacancy_title="Data Analyst",
        company="TechCorp",
        requirements="SQL, Python",
        resume_context="profile text",
    )
    assert "Data Analyst" in prompt
    assert "TechCorp" in prompt
    assert "SQL, Python" in prompt


def test_prompt_forbids_inventing_experience():
    """Prompt must instruct the model not to invent years/skills."""
    prompt = build_coverletter_prompt(
        vacancy_title="Dev",
        company="Co",
        requirements="",
        resume_context="profile",
    )
    lower = prompt.lower()
    assert "не выдумывай" in lower or "только факты" in lower


def test_prompt_forbids_signature_and_placeholders():
    """Prompt must forbid signatures and placeholders."""
    prompt = build_coverletter_prompt(
        vacancy_title="Dev",
        company="Co",
        requirements="",
        resume_context="profile",
    )
    lower = prompt.lower()
    assert "подпись" in lower or "с уважением" in lower
    assert "ваше имя" in lower or "placeholder" in lower or "плейсхолдер" in lower


def test_prompt_requires_russian():
    """Prompt must explicitly require Russian language."""
    prompt = build_coverletter_prompt(
        vacancy_title="Dev",
        company="Co",
        requirements="",
        resume_context="profile",
    )
    lower = prompt.lower()
    assert "русск" in lower


def test_prompt_specifies_format():
    """Prompt must specify multi-paragraph format and character count."""
    prompt = build_coverletter_prompt(
        vacancy_title="Dev",
        company="Co",
        requirements="",
        resume_context="profile",
    )
    lower = prompt.lower()
    assert "1200" in prompt
    assert "2200" in prompt


def test_prompt_starts_with_greeting_instruction():
    """Prompt must instruct to start with greeting."""
    prompt = build_coverletter_prompt(
        vacancy_title="Dev",
        company="Co",
        requirements="",
        resume_context="profile",
    )
    assert "\u0417\u0434\u0440\u0430\u0432\u0441\u0442\u0432\u0443\u0439\u0442\u0435" in prompt
