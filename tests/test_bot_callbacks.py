import pytest

pytest.importorskip("telegram")

import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock

from app.bot import main


def test_on_button_coverletter_sends_placeholder() -> None:
    query = SimpleNamespace(
        data="coverletter",
        answer=AsyncMock(),
        message=SimpleNamespace(reply_text=AsyncMock()),
    )
    update = SimpleNamespace(callback_query=query, effective_chat=SimpleNamespace(id=1))

    asyncio.run(main.on_button(update, ctx=SimpleNamespace()))

    query.answer.assert_awaited_once()
    query.message.reply_text.assert_awaited_once_with("Функция будет доступна на Stage 3")
