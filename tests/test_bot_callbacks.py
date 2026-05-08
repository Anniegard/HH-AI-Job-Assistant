import pytest

pytest.importorskip("telegram")

import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

from app.bot import main


def test_on_button_coverletter_saves_to_sheet() -> None:
    main._state.clear()
    main._state[1]["current"] = SimpleNamespace(id="1", url="https://hh.ru/v/1")

    query = SimpleNamespace(
        data="coverletter",
        answer=AsyncMock(),
        message=SimpleNamespace(reply_text=AsyncMock()),
    )
    update = SimpleNamespace(callback_query=query, effective_chat=SimpleNamespace(id=1))

    main._openai.generate_cover_letter = lambda **_: "Generated cover letter"
    update_cover_mock = MagicMock(return_value=True)
    main._sheets.update_cover_letter = update_cover_mock

    asyncio.run(main.on_button(update, ctx=SimpleNamespace()))

    query.answer.assert_awaited_once()
    update_cover_mock.assert_called_once_with("https://hh.ru/v/1", "Generated cover letter")
    query.message.reply_text.assert_awaited_once_with("✉️ Сопроводительное письмо:\n\nGenerated cover letter")
