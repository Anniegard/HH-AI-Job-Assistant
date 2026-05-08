from __future__ import annotations

import pytest

pytest.importorskip("telegram")

from app.bot import main as bot_main


@pytest.mark.asyncio
async def test_load_queue_filters_seen_ids_from_crm(monkeypatch: pytest.MonkeyPatch) -> None:
    class MockHH:
        async def search_vacancies(self, **kwargs):
            return {
                "items": [
                    {"id": "1", "name": "A", "alternate_url": "https://x/1", "employer": {"name": "E"}},
                    {"id": "2", "name": "B", "alternate_url": "https://x/2", "employer": {"name": "E"}},
                ]
            }

    class MockCRM:
        async def get_seen_ids(self, chat_id: int) -> set[str]:
            return {"1"}

    monkeypatch.setattr(bot_main, "HHClient", MockHH)
    monkeypatch.setattr(bot_main, "_crm", MockCRM())
    bot_main._state.clear()

    await bot_main._load_queue(chat_id=42)

    ids = [v.id for v in bot_main._state[42]["queue"]]
    assert ids == ["2"]


@pytest.mark.asyncio
async def test_restart_and_same_hh_results_do_not_show_duplicate(monkeypatch: pytest.MonkeyPatch) -> None:
    crm_seen: set[tuple[int, str]] = set()

    class MockHH:
        async def search_vacancies(self, **kwargs):
            return {
                "items": [
                    {"id": "dup-1", "name": "A", "alternate_url": "https://x/1", "employer": {"name": "E"}},
                    {"id": "dup-2", "name": "B", "alternate_url": "https://x/2", "employer": {"name": "E"}},
                ]
            }

    class MockCRM:
        async def get_seen_ids(self, chat_id: int) -> set[str]:
            return {v for c, v in crm_seen if c == chat_id}

        async def save_action(self, action) -> None:
            crm_seen.add((action.chat_id, action.vacancy_id))

    monkeypatch.setattr(bot_main, "HHClient", MockHH)
    monkeypatch.setattr(bot_main, "_crm", MockCRM())
    bot_main._state.clear()

    # Первая "сессия": пользователь увидел первую вакансию.
    await bot_main._load_queue(chat_id=100)
    first = bot_main._state[100]["queue"][0]
    await bot_main._crm.save_action(bot_main.CRMAction(chat_id=100, vacancy_id=first.id, action="viewed"))

    # "Рестарт": очищаем in-memory стейт.
    bot_main._state.clear()

    # Вторая сессия: HH отдаёт ту же выдачу, но дубль не должен попасть в очередь.
    await bot_main._load_queue(chat_id=100)
    ids_after_restart = [v.id for v in bot_main._state[100]["queue"]]
    assert "dup-1" not in ids_after_restart
    assert ids_after_restart == ["dup-2"]
