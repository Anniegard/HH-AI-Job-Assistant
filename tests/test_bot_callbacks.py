import pytest

pytest.importorskip("telegram")

import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

from app.bot import main
from app.services.vacancy import Vacancy


def _make_coverletter_update(chat_id=1):
    query = SimpleNamespace(
        data="coverletter",
        answer=AsyncMock(),
        message=SimpleNamespace(reply_text=AsyncMock()),
    )
    update = SimpleNamespace(callback_query=query, effective_chat=SimpleNamespace(id=chat_id))
    return update, query


def test_on_button_coverletter_no_vacancy_shows_error():
    """No current vacancy -> bot returns error message, does not crash."""
    main._state.clear()
    update, query = _make_coverletter_update(chat_id=100)

    asyncio.run(main.on_button(update, ctx=SimpleNamespace()))

    query.answer.assert_awaited_once()
    call_args = query.message.reply_text.call_args[0][0]
    assert "\u26a0\ufe0f" in call_args  # warning emoji


def test_on_button_coverletter_sends_letter(monkeypatch):
    """With a vacancy and working OpenAI - letter is sent."""
    chat_id = 200
    main._state.clear()

    vacancy = Vacancy(id="v1", name="Python Dev", employer="ACME", url="https://hh.ru/v/1")
    main._state[chat_id]["current"] = vacancy

    fake_letter = "Hello! I want to apply for the Python Dev position."
    monkeypatch.setattr(main._openai, "generate_cover_letter", MagicMock(return_value=fake_letter))
    monkeypatch.setattr(
        main,
        "_sheets",
        SimpleNamespace(
            update_cover_letter=MagicMock(return_value=True),
            list_seen_urls=MagicMock(return_value=set()),
        ),
    )

    update, query = _make_coverletter_update(chat_id=chat_id)
    asyncio.run(main.on_button(update, ctx=SimpleNamespace()))

    query.answer.assert_awaited_once()
    sent = query.message.reply_text.call_args[0][0]
    assert fake_letter in sent
    assert "\u2709\ufe0f" in sent  # envelope emoji
