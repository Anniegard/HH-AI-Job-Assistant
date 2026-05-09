import pytest

pytest.importorskip("telegram")
pytest.importorskip("pydantic_settings")

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

from app.bot import main as bot_main
from app.services.vacancy import Vacancy


def _mock_crm(
    *,
    load_jobs=None,
    should_skip=False,
    upsert_job=None,
    update_status=None,
    save_letter=None,
):
    crm = MagicMock()
    crm.load_jobs.return_value = load_jobs or []
    crm.should_skip.return_value = should_skip
    crm.upsert_job.return_value = None
    crm.update_status.return_value = True
    crm.save_letter.return_value = True
    if upsert_job is not None:
        crm.upsert_job = upsert_job
    if update_status is not None:
        crm.update_status = update_status
    if save_letter is not None:
        crm.save_letter = save_letter
    return crm


@pytest.mark.asyncio
async def test_status_flow_viewed_saved_hidden(monkeypatch):
    chat_id = 42
    bot_main._state.clear()

    vacancy = Vacancy(
        id="1", name="Python Dev", employer="ACME", area="Remote", url="https://hh.ru/v/1"
    )

    upsert = MagicMock()
    update_status = MagicMock(return_value=True)
    mock_crm = _mock_crm(upsert_job=upsert, update_status=update_status)
    monkeypatch.setattr(bot_main, "_crm", mock_crm)

    msg = SimpleNamespace(
        reply_text=AsyncMock(), chat=SimpleNamespace(send_action=AsyncMock())
    )
    update_obj = SimpleNamespace(
        effective_chat=SimpleNamespace(id=chat_id), message=msg, callback_query=None
    )

    bot_main._state[chat_id]["queue"] = [vacancy]
    await bot_main._show_next(update_obj, chat_id, None)

    upsert.assert_called_once()
    call_job = upsert.call_args[0][0]
    assert call_job["status"] == "viewed"

    await bot_main.cmd_save(update_obj, None)
    update_status.assert_any_call("1", "saved")

    bot_main._state[chat_id]["current"] = vacancy
    bot_main._state[chat_id]["queue"] = []
    monkeypatch.setattr(bot_main, "_load_queue", AsyncMock(return_value=None))
    await bot_main.cmd_hide(update_obj, None)
    update_status.assert_any_call("1", "hidden")


@pytest.mark.asyncio
async def test_cmd_coverletter_sends_letter_and_saves_to_crm(monkeypatch):
    chat_id = 55
    bot_main._state.clear()

    vacancy = Vacancy(
        id="v55", name="AI Engineer", employer="Skynet", url="https://hh.ru/v/55"
    )
    bot_main._state[chat_id]["current"] = vacancy

    fake_letter = "Hello! I want to work at Skynet as AI Engineer."
    monkeypatch.setattr(
        bot_main._openai, "generate_cover_letter", MagicMock(return_value=fake_letter)
    )

    save_letter_mock = MagicMock(return_value=True)
    mock_crm = _mock_crm(save_letter=save_letter_mock)
    monkeypatch.setattr(bot_main, "_crm", mock_crm)

    msg = SimpleNamespace(reply_text=AsyncMock())
    update_obj = SimpleNamespace(
        effective_chat=SimpleNamespace(id=chat_id), message=msg, callback_query=None
    )

    await bot_main.cmd_coverletter(update_obj, None)

    sent = msg.reply_text.call_args[0][0]
    assert fake_letter in sent
    save_letter_mock.assert_called_once_with("v55", fake_letter)


@pytest.mark.asyncio
async def test_cmd_coverletter_no_vacancy_shows_error(monkeypatch):
    chat_id = 66
    bot_main._state.clear()

    msg = SimpleNamespace(reply_text=AsyncMock())
    update_obj = SimpleNamespace(
        effective_chat=SimpleNamespace(id=chat_id), message=msg, callback_query=None
    )

    await bot_main.cmd_coverletter(update_obj, None)

    sent = msg.reply_text.call_args[0][0]
    assert "⚠️" in sent


@pytest.mark.asyncio
async def test_show_next_does_not_dedupe_by_empty_url(monkeypatch):
    chat_id = 99
    bot_main._state.clear()

    first = Vacancy(id="1", name="Python Dev 1", employer="ACME", area="Remote", url="")
    second = Vacancy(id="2", name="Python Dev 2", employer="ACME", area="Remote", url="")

    mock_crm = _mock_crm()
    monkeypatch.setattr(bot_main, "_crm", mock_crm)

    msg = SimpleNamespace(
        reply_text=AsyncMock(), chat=SimpleNamespace(send_action=AsyncMock())
    )
    update_obj = SimpleNamespace(
        effective_chat=SimpleNamespace(id=chat_id), message=msg, callback_query=None
    )

    bot_main._state[chat_id]["queue"] = [first, second]

    await bot_main._show_next(update_obj, chat_id, None)
    await bot_main._show_next(update_obj, chat_id, None)

    assert msg.reply_text.await_count == 2


@pytest.mark.asyncio
async def test_show_next_skips_crm_hidden(monkeypatch):
    chat_id = 77
    bot_main._state.clear()

    hidden = Vacancy(
        id="h1", name="Hidden Job", employer="Corp", url="https://hh.ru/vacancy/h1"
    )
    visible = Vacancy(
        id="v1", name="Visible Job", employer="Corp", url="https://hh.ru/vacancy/v1"
    )

    mock_crm = MagicMock()
    mock_crm.load_jobs.return_value = []
    mock_crm.should_skip.side_effect = lambda vid: vid == "h1"
    mock_crm.upsert_job.return_value = None
    monkeypatch.setattr(bot_main, "_crm", mock_crm)

    msg = SimpleNamespace(
        reply_text=AsyncMock(), chat=SimpleNamespace(send_action=AsyncMock())
    )
    update_obj = SimpleNamespace(
        effective_chat=SimpleNamespace(id=chat_id), message=msg, callback_query=None
    )

    bot_main._state[chat_id]["queue"] = [hidden, visible]
    await bot_main._show_next(update_obj, chat_id, None)

    sent = msg.reply_text.call_args[0][0]
    assert "Visible Job" in sent
