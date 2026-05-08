"""Telegram-бот, Stage 1.

Запуск: python -m app.bot.main
Использует polling. Хранит viewed_ids в памяти процесса.
"""

from __future__ import annotations

import asyncio
from collections import defaultdict

from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import (
    Application,
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
)

from app.core.config import settings
from app.core.logging import logger
from app.services.hh_client import HHClient, HHClientError
from app.services.vacancy import Vacancy

# In-memory: chat_id -> set(vacancy_id). Stage 2 переедет в Google Sheets.
_viewed: dict[int, set[str]] = defaultdict(set)

# Стартовый запрос — позже вынесем в /settings или конфиг профиля.
DEFAULT_QUERY = "Python AI automation"
DEFAULT_PER_PAGE = 20


async def cmd_start(update: Update, _: ContextTypes.DEFAULT_TYPE) -> None:
    text = (
        "👋 Привет! Я HH AI Job Assistant.\n\n"
        "Команды:\n"
        "/jobs — показать свежую вакансию\n"
        "/next — следующая (Stage 2)\n"
        "/save — сохранить (Stage 2)\n"
        "/coverletter — сгенерировать сопроводительное (Stage 3)\n"
    )
    await update.message.reply_text(text)


async def cmd_jobs(update: Update, _: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.effective_chat.id
    await update.message.chat.send_action("typing")

    client = HHClient()
    try:
        raw = await client.search_vacancies(
            text=DEFAULT_QUERY,
            per_page=DEFAULT_PER_PAGE,
            page=0,
        )
    except HHClientError as e:
        logger.error(f"HH error: {e}")
        await update.message.reply_text(f"⚠️ Ошибка HH API: {e}")
        return

    items = raw.get("items", [])
    if not items:
        await update.message.reply_text("Ничего не нашлось 🤷")
        return

    seen = _viewed[chat_id]
    for item in items:
        vid = str(item["id"])
        if vid in seen:
            continue
        vacancy = Vacancy.from_hh(item)
        seen.add(vid)
        await update.message.reply_text(
            vacancy.short_text(),
            parse_mode=ParseMode.HTML,
            disable_web_page_preview=True,
        )
        return

    await update.message.reply_text(
        "Все вакансии из текущей выдачи уже показывал. "
        "В Stage 2 будет нормальная пагинация и фильтры 🙂"
    )


def build_app() -> Application:
    if not settings.telegram_token:
        raise RuntimeError(
            "TELEGRAM_TOKEN не задан. Заполни .env (см. .env.example)."
        )

    app = ApplicationBuilder().token(settings.telegram_token).build()
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("jobs", cmd_jobs))
    return app


async def main() -> None:
    logger.info("Starting Telegram bot (polling)")
    app = build_app()
    # PTB v21 использует run_polling с собственным event loop;
    # здесь оборачиваем для запуска через python -m
    await app.initialize()
    await app.start()
    await app.updater.start_polling()
    logger.info("Bot started. Press Ctrl+C to stop.")
    try:
        # Ждём бесконечно, пока процесс не убьют
        await asyncio.Event().wait()
    finally:
        await app.updater.stop()
        await app.stop()
        await app.shutdown()


if __name__ == "__main__":
    asyncio.run(main())
