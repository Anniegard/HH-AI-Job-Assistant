from __future__ import annotations

import asyncio
from collections import defaultdict

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.constants import ParseMode
from telegram.ext import (
    Application,
    ApplicationBuilder,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
)

from app.core.config import settings
from app.core.logging import logger
from app.scoring.engine import ScoringEngine
from app.services.crm_mapper import vacancy_to_crm_row
from app.services.hh_client import HHClient, HHClientError
from app.services.sheets_client import SheetsClient, SheetsClientError
from app.services.vacancy import Vacancy

DEFAULT_QUERY = "Python AI automation"
DEFAULT_PER_PAGE = 20


def _new_state() -> dict:
    return {"queue": [], "cursor": 0, "current": None, "seen": set(), "saved": set(), "hidden": set(), "scores": {}}


_state: dict[int, dict] = defaultdict(_new_state)
_scorer = ScoringEngine()
_sheets = SheetsClient()


def _buttons(vacancy_id: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [[InlineKeyboardButton("👍 Next", callback_data="next"), InlineKeyboardButton("👎 Hide", callback_data=f"hide:{vacancy_id}")],
         [InlineKeyboardButton("📌 Save", callback_data=f"save:{vacancy_id}"), InlineKeyboardButton("✉", callback_data="coverletter")]]
    )


async def _load_queue(chat_id: int) -> None:
    client = HHClient()
    raw = await client.search_vacancies(text=DEFAULT_QUERY, per_page=DEFAULT_PER_PAGE, page=0)
    queue = [Vacancy.from_hh(item) for item in raw.get("items", [])]
    _state[chat_id]["queue"] = queue
    _state[chat_id]["cursor"] = 0


async def _show_next(update: Update, chat_id: int, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    st = _state[chat_id]
    if not st["queue"] or st["cursor"] >= len(st["queue"]):
        await _load_queue(chat_id)

    while st["cursor"] < len(st["queue"]):
        vacancy = st["queue"][st["cursor"]]
        st["cursor"] += 1
        if vacancy.id in st["seen"] or vacancy.id in st["hidden"]:
            continue
        st["seen"].add(vacancy.id)
        st["current"] = vacancy
        score, reasons = _scorer.score(vacancy.model_dump())
        st["scores"][vacancy.id] = (score, reasons)
        try:
            _sheets.append_vacancy(vacancy_to_crm_row(vacancy, score, reasons, status="viewed"))
        except SheetsClientError as e:
            logger.warning("Failed to append viewed vacancy to sheet: %s", e)
        score_line = f"\n\n🎯 Score: <b>{score}/100</b>"
        if reasons:
            score_line += f"\nПочему: {', '.join(reasons[:3])}"

        target = update.message if update.message else update.callback_query.message
        await target.reply_text(
            vacancy.short_text() + score_line,
            parse_mode=ParseMode.HTML,
            disable_web_page_preview=True,
            reply_markup=_buttons(vacancy.id),
        )
        return

    target = update.message if update.message else update.callback_query.message
    await target.reply_text("Не осталось новых вакансий в выдаче. Попробуй /jobs позже.")


async def cmd_start(update: Update, _: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text("👋 Привет! Команды: /jobs /next /save /hide")


async def cmd_jobs(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.effective_chat.id
    await update.message.chat.send_action("typing")
    try:
        await _show_next(update, chat_id, ctx)
    except HHClientError as e:
        logger.error(f"HH error: {e}")
        await update.message.reply_text(f"⚠️ Ошибка HH API: {e}")


async def cmd_next(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    await _show_next(update, update.effective_chat.id, ctx)


async def cmd_save(update: Update, _: ContextTypes.DEFAULT_TYPE) -> None:
    st = _state[update.effective_chat.id]
    cur: Vacancy | None = st.get("current")
    if not cur:
        await update.message.reply_text("Сначала покажи вакансию: /jobs")
        return
    st["saved"].add(cur.id)
    _sheets.update_status(cur.url, "saved")
    await update.message.reply_text("📌 Сохранено")


async def cmd_hide(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    st = _state[update.effective_chat.id]
    cur: Vacancy | None = st.get("current")
    if cur:
        st["hidden"].add(cur.id)
        _sheets.update_status(cur.url, "hidden")
    await _show_next(update, update.effective_chat.id, ctx)




async def cmd_coverletter(update: Update, _: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text("Функция будет доступна на Stage 3")


async def on_button(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    action, _, vacancy_id = (query.data or "").partition(":")

    if action == "next":
        await _show_next(update, update.effective_chat.id, ctx)
    elif action == "save":
        st = _state[update.effective_chat.id]
        if vacancy_id:
            st["saved"].add(vacancy_id)
            cur: Vacancy | None = st.get("current")
            if cur and cur.id == vacancy_id:
                _sheets.update_status(cur.url, "saved")
            await query.message.reply_text("📌 Сохранено")
    elif action == "hide":
        st = _state[update.effective_chat.id]
        if vacancy_id:
            st["hidden"].add(vacancy_id)
            cur: Vacancy | None = st.get("current")
            if cur and cur.id == vacancy_id:
                _sheets.update_status(cur.url, "hidden")
        await _show_next(update, update.effective_chat.id, ctx)
    elif action == "coverletter":
        await query.message.reply_text("Функция будет доступна на Stage 3")


def build_app() -> Application:
    if not settings.telegram_token:
        raise RuntimeError("TELEGRAM_TOKEN не задан. Заполни .env (см. .env.example).")

    app = ApplicationBuilder().token(settings.telegram_token).build()
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("jobs", cmd_jobs))
    app.add_handler(CommandHandler("next", cmd_next))
    app.add_handler(CommandHandler("save", cmd_save))
    app.add_handler(CommandHandler("hide", cmd_hide))
    app.add_handler(CommandHandler("coverletter", cmd_coverletter))
    app.add_handler(CallbackQueryHandler(on_button))
    return app


async def main() -> None:
    logger.info("Starting Telegram bot (polling)")
    app = build_app()
    await app.initialize()
    await app.start()
    await app.updater.start_polling()
    logger.info("Bot started. Press Ctrl+C to stop.")
    try:
        await asyncio.Event().wait()
    finally:
        await app.updater.stop()
        await app.stop()
        await app.shutdown()


if __name__ == "__main__":
    asyncio.run(main())
