import pytest
pytest.importorskip("telegram")
pytest.importorskip("pydantic_settings")

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

from app.bot import main as bot_main
from app.services.vacancy import Vacancy


@pytest.mark.asyncio
async def test_status_flow_viewed_saved_hidden(monkeypatch):
    chat_id = 42
    bot_main._state.clear()

    vacancy = Vacancy(id="1", name="Python Dev", employer="ACME", area="Remote", url="https://hh.ru/v/1")

    append = MagicMock()
    update_mock = MagicMock(return_value=True)
    monkeypatch.setattr(
        bot_main,
        "_sheets",
        SimpleNamespace(append_vacancy=append, update_status=update_mock, list_seen_urls=MagicMock(return_value=set())),
    )

    msg = SimpleNamespace(reply_text=AsyncMock(), chat=SimpleNamespace(send_action=AsyncMock()))
    update_obj = SimpleNamespace(effective_chat=SimpleNamespace(id=chat_id), message=msg, callback_query=None)

    bot_main._state[chat_id]["queue"] = [vacancy]
    await bot_main._show_next(update_obj, chat_id, None)
    append.assert_called_once()
    assert append.call_args.args[0][5] == "viewed"

    await bot_main.cmd_save(update_obj, None)
    update_mock.assert_any_call("https://hh.ru/v/1", "saved")

    bot_main._state[chat_id]["current"] = vacancy
    bot_main._state[chat_id]["queue"] = []
    monkeypatch.setattr(bot_main, "_load_queue", AsyncMock(return_value=None))
    await bot_main.cmd_hide(update_obj, None)
    update_mock.assert_any_call("https://hh.ru/v/1", "hidden")


@pytest.mark.asyncio
async def test_cmd_coverletter_sends_letter_and_saves_to_sheets(monkeypatch):
    """cmd_coverletter sends letter and saves to Sheets."""
    chat_id = 55
    bot_main._state.clear()

    vacancy = Vacancy(id="v55", name="AI Engineer", employer="Skynet", url="https://hh.ru/v/55")
    bot_main._state[chat_id]["current"] = vacancy

    fake_letter = "Hello! I want to work at Skynet as AI Engineer."
    monkeypatch.setattr(bot_main._openai, "generate_cover_letter", MagicMock(return_value=fake_letter))

    update_cover = MagicMock(return_value=True)
    monkeypatch.setattr(
        bot_main,
        "_sheets",
        SimpleNamespace(
            update_cover_letter=update_cover,
            list_seen_urls=MagicMock(return_value=set()),
        ),
    )

    msg = SimpleNamespace(reply_text=AsyncMock())
    update_obj = SimpleNamespace(effective_chat=SimpleNamespace(id=chat_id), message=msg, callback_query=None)

    await bot_main.cmd_coverletter(update_obj, None)

    sent = msg.reply_text.call_args[0][0]
    assert fake_letter in sent
    update_cover.assert_called_once_with("https://hh.ru/v/55", fake_letter)


@pytest.mark.asyncio
async def test_cmd_coverletter_no_vacancy_shows_error(monkeypatch):
    """cmd_coverletter without current vacancy sends error."""
    chat_id = 66
    bot_main._state.clear()

    msg = SimpleNamespace(reply_text=AsyncMock())
    update_obj = SimpleNamespace(effective_chat=SimpleNamespace(id=chat_id), message=msg, callback_query=None)

    await bot_main.cmd_coverletter(update_obj, None)

    sent = msg.reply_text.call_args[0][0]
    assert "\u26a0\ufe0f" in sent  # warning emoji


@pytest.mark.asyncio
async def test_show_next_does_not_dedupe_by_empty_url(monkeypatch):
    chat_id = 99
    bot_main._state.clear()

    first = Vacancy(id="1", name="Python Dev 1", employer="ACME", area="Remote", url="")
    second = Vacancy(id="2", name="Python Dev 2", employer="ACME", area="Remote", url="")

    append = MagicMock()
    monkeypatch.setattr(
        bot_main,
        "_sheets",
        SimpleNamespace(append_vacancy=append, update_status=MagicMock(), list_seen_urls=MagicMock(return_value=set())),
    )

    msg = SimpleNamespace(reply_text=AsyncMock(), chat=SimpleNamespace(send_action=AsyncMock()))
    update_obj = SimpleNamespace(effective_chat=SimpleNamespace(id=chat_id), message=msg, callback_query=None)

    bot_main._state[chat_id]["queue"] = [first, second]

    await bot_main._show_next(update_obj, chat_id, None)
    await bot_main._show_next(update_obj, chat_id, None)

    assert msg.reply_text.await_count == 2
