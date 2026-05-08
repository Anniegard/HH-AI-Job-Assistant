"""Tests for OpenAI client - no real API calls."""

from __future__ import annotations

import pytest
from unittest.mock import MagicMock, patch

from app.services.openai_client import OpenAIClient, OpenAIClientError


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
