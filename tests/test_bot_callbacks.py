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


def _mock_crm():
    crm = MagicMock()
    crm.load_jobs.return_value = []
    crm.should_skip.return_value = False
    crm.upsert_job.return_value = None
    crm.update_status.return_value = True
    crm.save_letter.return_value = True
    return crm


def test_on_button_coverletter_no_vacancy_shows_error():
    """No current vacancy -> bot returns error message, does not crash."""
    main._state.clear()
    update, query = _make_coverletter_update(chat_id=100)

    asyncio.run(main.on_button(update, ctx=SimpleNamespace()))

    query.answer.assert_awaited_once()
    call_args = query.message.reply_text.call_args[0][0]
    assert "⚠️" in call_args  # warning emoji


def test_on_button_coverletter_sends_letter(monkeypatch):
    """With a vacancy and working OpenAI - letter is sent."""
    chat_id = 200
    main._state.clear()

    vacancy = Vacancy(id="v1", name="Python Dev", employer="ACME", url="https://hh.ru/v/1")
    main._state[chat_id]["current"] = vacancy

    fake_letter = "Hello! I want to apply for the Python Dev position."
    monkeypatch.setattr(main._openai, "generate_cover_letter", MagicMock(return_value=fake_letter))
    monkeypatch.setattr(
        main.HHClient,
        "get_vacancy",
        AsyncMock(return_value={"description": "<p>Python developer needed</p>"}),
    )
    mock_crm = _mock_crm()
    monkeypatch.setattr(main, "_crm", mock_crm)

    update, query = _make_coverletter_update(chat_id=chat_id)
    asyncio.run(main.on_button(update, ctx=SimpleNamespace()))

    query.answer.assert_awaited_once()
    sent = query.message.reply_text.call_args[0][0]
    assert fake_letter in sent
    mock_crm.save_letter.assert_called_once_with("v1", fake_letter)


def test_on_button_save_calls_crm(monkeypatch):
    """Inline save button updates CRM status to saved."""
    chat_id = 300
    main._state.clear()

    vacancy = Vacancy(id="vSave", name="Dev", employer="Corp", url="https://hh.ru/vacancy/vSave")
    main._state[chat_id]["current"] = vacancy

    mock_crm = _mock_crm()
    monkeypatch.setattr(main, "_crm", mock_crm)

    query = SimpleNamespace(
        data="save:vSave",
        answer=AsyncMock(),
        message=SimpleNamespace(reply_text=AsyncMock()),
    )
    update = SimpleNamespace(callback_query=query, effective_chat=SimpleNamespace(id=chat_id))
    asyncio.run(main.on_button(update, ctx=SimpleNamespace()))

    mock_crm.update_status.assert_called_once_with("vSave", "saved")


def test_on_button_hide_calls_crm(monkeypatch):
    """Inline hide button updates CRM status to hidden."""
    chat_id = 400
    main._state.clear()

    mock_crm = _mock_crm()
    monkeypatch.setattr(main, "_crm", mock_crm)
    monkeypatch.setattr(main, "_load_queue", AsyncMock(return_value=None))

    query = SimpleNamespace(
        data="hide:vHide",
        answer=AsyncMock(),
        message=SimpleNamespace(reply_text=AsyncMock()),
    )
    update = SimpleNamespace(
        callback_query=query, effective_chat=SimpleNamespace(id=chat_id), message=None
    )
    asyncio.run(main.on_button(update, ctx=SimpleNamespace()))

    mock_crm.update_status.assert_called_once_with("vHide", "hidden")


# ---------------------------------------------------------------------------
# /daily letter button — _send_coverletter_by_id fallback tests
# ---------------------------------------------------------------------------


def _make_daily_coverletter_update(vacancy_id: str, chat_id: int = 500):
    """Build an Update for a /daily [Letter] button click (coverletter:{id})."""
    query = SimpleNamespace(
        data=f"coverletter:{vacancy_id}",
        answer=AsyncMock(),
        message=SimpleNamespace(reply_text=AsyncMock()),
    )
    return (
        SimpleNamespace(callback_query=query, effective_chat=SimpleNamespace(id=chat_id)),
        query,
    )


def test_daily_coverletter_uses_vacancy_cache(monkeypatch):
    """Letter button on /daily card: vacancy found in cache → letter sent."""
    chat_id = 500
    main._state.clear()

    vacancy = Vacancy(id="d1", name="AI Engineer", employer="Lab", url="https://hh.ru/v/d1")
    main._state[chat_id]["vacancy_cache"]["d1"] = vacancy

    fake_letter = "Cache-path letter."
    monkeypatch.setattr(main._openai, "generate_cover_letter", MagicMock(return_value=fake_letter))
    # get_vacancy is called by _generate_coverletter for the full description
    monkeypatch.setattr(
        main.HHClient, "get_vacancy",
        AsyncMock(return_value={"description": "<p>AI tasks</p>"}),
    )
    mock_crm = _mock_crm()
    monkeypatch.setattr(main, "_crm", mock_crm)

    update, query = _make_daily_coverletter_update("d1", chat_id)
    asyncio.run(main.on_button(update, ctx=SimpleNamespace()))

    query.answer.assert_awaited_once()
    sent = query.message.reply_text.call_args[0][0]
    assert fake_letter in sent


def test_daily_coverletter_fallback_fetches_from_hh(monkeypatch):
    """If vacancy not in cache, falls back to HH API and still sends letter."""
    chat_id = 501
    main._state.clear()
    # vacancy_cache is empty — fallback path triggers

    raw_hh = {
        "id": "d2",
        "name": "LLM Specialist",
        "employer": {"name": "AI Corp"},
        "alternate_url": "https://hh.ru/v/d2",
        "area": {"name": "Moscow"},
        "salary": None,
        "schedule": {"id": "remote"},
        "experience": {"id": "between1And3"},
        "snippet": {"requirement": "LLM skills", "responsibility": "Build agents"},
        "published_at": "2026-05-10T00:00:00+0000",
        "description": "<p>Build LLM agents</p>",
    }
    # get_vacancy called twice: once for fallback fetch, once for full description
    monkeypatch.setattr(main.HHClient, "get_vacancy", AsyncMock(return_value=raw_hh))

    fake_letter = "Fallback-path letter."
    monkeypatch.setattr(main._openai, "generate_cover_letter", MagicMock(return_value=fake_letter))
    mock_crm = _mock_crm()
    monkeypatch.setattr(main, "_crm", mock_crm)

    update, query = _make_daily_coverletter_update("d2", chat_id)
    asyncio.run(main.on_button(update, ctx=SimpleNamespace()))

    query.answer.assert_awaited_once()
    sent = query.message.reply_text.call_args[0][0]
    assert fake_letter in sent
    # Vacancy must be cached after successful fallback fetch
    assert "d2" in main._state[chat_id]["vacancy_cache"]


def test_daily_coverletter_fallback_hh_error_shows_warning(monkeypatch):
    """If fallback HH fetch fails, user gets an error message, no crash."""
    chat_id = 502
    main._state.clear()
    # vacancy_cache is empty, and HH API will fail

    from app.services.hh_client import HHClientError

    monkeypatch.setattr(
        main.HHClient, "get_vacancy", AsyncMock(side_effect=HHClientError("403 Forbidden"))
    )
    mock_crm = _mock_crm()
    monkeypatch.setattr(main, "_crm", mock_crm)

    update, query = _make_daily_coverletter_update("d3", chat_id)
    asyncio.run(main.on_button(update, ctx=SimpleNamespace()))

    query.answer.assert_awaited_once()
    sent = query.message.reply_text.call_args[0][0]
    assert "⚠️" in sent
