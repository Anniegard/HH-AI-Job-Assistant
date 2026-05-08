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
from app.core.resume import load_resume_context
from app.scoring.engine import ScoringEngine
from app.services.crm_mapper import vacancy_to_crm_row
from app.services.hh_client import HHClient, HHClientError
from app.services.openai_client import OpenAIClient, OpenAIClientError
from app.services.sheets_client import SheetsClient, SheetsClientError
from app.services.vacancy import Vacancy

DEFAULT_QUERY = "Python AI automation"
DEFAULT_PER_PAGE = 20


def _new_state() -> dict:
    return {
        "queue": [],
        "cursor": 0,
        "current": None,
        "seen": set(),
        "saved": set(),
        "hidden": set(),
        "scores": {},
        "sheet_seen_urls_loaded": False,
    }


_state: dict[int, dict] = defaultdict(_new_state)
_scorer = ScoringEngine()
_sheets = SheetsClient()
_openai = OpenAIClient()


def _buttons(vacancy_id: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("\U0001f44d Далее", callback_data="next"),
                InlineKeyboardButton("\U0001f44e Скрыть", callback_data=f"hide:{vacancy_id}"),
            ],
            [
                InlineKeyboardButton("\U0001f4cc Сохранить", callback_data=f"save:{vacancy_id}"),
                InlineKeyboardButton("✉ Письмо", callback_data="coverletter"),
            ],
        ]
    )


async def _load_queue(chat_id: int) -> None:
    client = HHClient()
    raw = await client.search_vacancies(text=DEFAULT_QUERY, per_page=DEFAULT_PER_PAGE, page=0)
    queue = [Vacancy.from_hh(item) for item in raw.get("items", [])]
    _state[chat_id]["queue"] = queue
    _state[chat_id]["cursor"] = 0


async def _show_next(update: Update, chat_id: int, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    st = _state[chat_id]
    if not st["sheet_seen_urls_loaded"]:
        try:
            st["seen"].update(_sheets.list_seen_urls())
        except SheetsClientError as e:
            logger.warning("Failed to preload seen vacancies from sheet: %s", e)
        st["sheet_seen_urls_loaded"] = True

    if not st["queue"] or st["cursor"] >= len(st["queue"]):
        await _load_queue(chat_id)

    while st["cursor"] < len(st["queue"]):
        vacancy = st["queue"][st["cursor"]]
        st["cursor"] += 1
        vacancy_url = vacancy.url.strip()
        seen_by_url = bool(vacancy_url) and vacancy_url in st["seen"]
        hidden_by_url = bool(vacancy_url) and vacancy_url in st["hidden"]
        if vacancy.id in st["seen"] or seen_by_url or vacancy.id in st["hidden"] or hidden_by_url:
            continue
        st["seen"].add(vacancy.id)
        if vacancy_url:
            st["seen"].add(vacancy_url)
        st["current"] = vacancy
        score, reasons = _scorer.score(vacancy.model_dump())
        st["scores"][vacancy.id] = (score, reasons)
        try:
            _sheets.append_vacancy(vacancy_to_crm_row(vacancy, score, reasons, status="viewed"))
        except SheetsClientError as e:
            logger.warning("Failed to append viewed vacancy to sheet: %s", e)
        score_line = f"\n\n\U0001f3af Оценка: <b>{score}/100</b>"
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
    await target.reply_text("Новых вакансий нет. Попробуй позже: /jobs")


async def cmd_start(update: Update, _: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text("\U0001f44b Привет! Команды: /jobs /next /save /hide /coverletter")


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
    cur = st.get("current")
    if not cur:
        await update.message.reply_text("Сначала открой вакансию: /jobs")
        return
    st["saved"].add(cur.id)
    if cur.url:
        st["saved"].add(cur.url)
    _sheets.update_status(cur.url, "saved")
    await update.message.reply_text("\U0001f4cc Сохранено")


async def cmd_hide(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    st = _state[update.effective_chat.id]
    cur = st.get("current")
    if cur:
        st["hidden"].add(cur.id)
        if cur.url:
            st["hidden"].add(cur.url)
        _sheets.update_status(cur.url, "hidden")
    await _show_next(update, update.effective_chat.id, ctx)


def _generate_coverletter(chat_id: int) -> tuple:
    """Generate letter, return (cover_letter, vacancy_url)."""
    st = _state[chat_id]
    cur = st.get("current")
    if not cur:
        raise OpenAIClientError("Сначала открой вакансию: /jobs")

    letter = _openai.generate_cover_letter(
        vacancy_title=cur.name,
        company=cur.employer,
        requirements=cur.snippet_requirement or "",
        user_profile=load_resume_context(),
    )
    return letter, cur.url or ""


async def _send_coverletter(chat_id: int, reply_fn) -> None:
    """Generate letter, send it, and save to Sheets."""
    try:
        cover_letter, vacancy_url = await asyncio.to_thread(_generate_coverletter, chat_id)
    except OpenAIClientError as e:
        await reply_fn(f"⚠️ {e}")
        return

    await reply_fn(f"✉️ Сопроводительное письмо:\n\n{cover_letter}")

    if vacancy_url:
        try:
            _sheets.update_cover_letter(vacancy_url, cover_letter)
        except SheetsClientError as e:
            logger.warning("Failed to save cover letter to sheet: %s", e)


async def cmd_coverletter(update: Update, _: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.effective_chat.id
    await _send_coverletter(chat_id, update.message.reply_text)


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
            cur = st.get("current")
            if cur and cur.id == vacancy_id:
                if cur.url:
                    st["saved"].add(cur.url)
                _sheets.update_status(cur.url, "saved")
            await query.message.reply_text("\U0001f4cc Сохранено")
    elif action == "hide":
        st = _state[update.effective_chat.id]
        if vacancy_id:
            st["hidden"].add(vacancy_id)
            cur = st.get("current")
            if cur and cur.id == vacancy_id:
                if cur.url:
                    st["hidden"].add(cur.url)
                _sheets.update_status(cur.url, "hidden")
        await _show_next(update, update.effective_chat.id, ctx)
    elif action == "coverletter":
        await _send_coverletter(update.effective_chat.id, query.message.reply_text)


def build_app() -> Application:
    if not settings.telegram_token:
        raise RuntimeError("TELEGRAM_TOKEN not set. Fill .env (see .env.example).")

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
