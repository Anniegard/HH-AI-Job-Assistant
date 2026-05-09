from __future__ import annotations

import asyncio
import re
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
from app.scoring.engine import ScoringEngine, ScoringResult
from app.services.crm_mapper import vacancy_to_crm_job
from app.services.hh_client import HHClient, HHClientError
from app.services.job_crm import JobCRM
from app.services.openai_client import OpenAIClient, OpenAIClientError
from app.services.sheets_client import SheetsClientError
from app.services.vacancy import Vacancy


def _strip_html(text: str) -> str:
    """Remove HTML tags and normalize whitespace from vacancy description."""
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


DEFAULT_QUERY = "Python AI automation"
DEFAULT_PER_PAGE = 20


def _new_state() -> dict:
    return {
        "queue": [],
        "cursor": 0,
        "current": None,
        # Within-session dedup set — prevents showing the same vacancy twice
        # in one session.  Cross-session state lives in the CRM / Sheet.
        "seen": set(),
        "scores": {},
        "crm_loaded": False,
        "debug": False,
    }


_state: dict[int, dict] = defaultdict(_new_state)
_scorer = ScoringEngine()
_crm = JobCRM()
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
                InlineKeyboardButton("\u2709 Письмо", callback_data="coverletter"),
            ],
        ]
    )


async def _load_queue(chat_id: int) -> None:
    client = HHClient()
    raw = await client.search_vacancies(text=DEFAULT_QUERY, per_page=DEFAULT_PER_PAGE, page=0)
    queue = [Vacancy.from_hh(item) for item in raw.get("items", [])]
    _state[chat_id]["queue"] = queue
    _state[chat_id]["cursor"] = 0


async def _build_scoring_payload(vacancy: Vacancy) -> dict:
    """Return a dict for ScoringEngine including full description when available."""
    payload = vacancy.model_dump()
    try:
        full = await HHClient().get_vacancy(vacancy.id)
        description_html = full.get("description", "") or ""
        payload["description"] = _strip_html(description_html)
    except HHClientError as e:
        logger.warning("Failed to fetch full vacancy %s for scoring: %s", vacancy.id, e)
        payload["description"] = ""
    return payload


def _format_score_block(result: ScoringResult) -> str:
    """Format the scoring block for Telegram display."""
    lines: list[str] = []
    lines.append(f"\n\n\U0001f3af <b>Оценка: {result.total_score}/100</b>")

    if not result.is_remote:
        lines.append("\u26a0\ufe0f <b>Формат: офис</b> (не удалённая/гибридная)")

    if result.strengths:
        top = ", ".join(result.strengths[:4])
        lines.append(f"\u2705 Совпадения: {top}")

    if result.risks:
        top_risks = ", ".join(result.risks[:3])
        lines.append(f"\u26a0\ufe0f Риски: {top_risks}")

    return "\n".join(lines)


def _format_debug_block(result: ScoringResult) -> str:
    """Format detailed per-component score breakdown for debug mode."""
    from app.scoring.engine import GROWTH_FIT_MAX, ROLE_FIT_MAX, STACK_FIT_MAX, TASK_FIT_MAX

    def _labels(lst: list) -> str:
        return ", ".join(lst) if lst else "\u2014"

    lines = ["\n\n\U0001f50d <b>Debug: разбивка очков</b>"]
    lines.append(
        f"  role   {result.role_fit:>3}/{ROLE_FIT_MAX}  "
        f"\u2192 {_labels(result.role_labels)}"
    )
    lines.append(
        f"  task   {result.task_fit:>3}/{TASK_FIT_MAX}  "
        f"\u2192 {_labels(result.task_labels)}"
    )
    lines.append(
        f"  stack  {result.stack_fit:>3}/{STACK_FIT_MAX}  "
        f"\u2192 {_labels(result.stack_labels)}"
    )
    lines.append(
        f"  growth {result.growth_fit:>3}/{GROWTH_FIT_MAX}  "
        f"\u2192 {_labels(result.growth_labels)}"
    )
    risk_str = _labels(result.risks) if result.risks else "\u2014"
    lines.append(f"  risk   {result.risk_penalty:>4}     \u2192 {risk_str}")
    lines.append(f"  <b>итого  {result.total_score:>3}/100</b>")
    lines.append(f"  {result.recommendation}")
    return "\n".join(lines)


async def _show_next(update: Update, chat_id: int, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    st = _state[chat_id]

    # Load CRM state once per session so should_skip() queries are in-memory.
    if not st["crm_loaded"]:
        try:
            _crm.load_jobs()
        except SheetsClientError as e:
            logger.warning("Failed to preload CRM state from sheet: %s", e)
        st["crm_loaded"] = True

    if not st["queue"] or st["cursor"] >= len(st["queue"]):
        await _load_queue(chat_id)

    while st["cursor"] < len(st["queue"]):
        vacancy = st["queue"][st["cursor"]]
        st["cursor"] += 1

        # Within-session dedup (same vacancy appearing twice in API results)
        if vacancy.id in st["seen"]:
            continue
        # Cross-session skip: hidden / applied / rejected in CRM
        if _crm.should_skip(vacancy.id):
            logger.info("Skipping vacancy %s (CRM status)", vacancy.id)
            continue

        st["seen"].add(vacancy.id)
        st["current"] = vacancy

        payload = await _build_scoring_payload(vacancy)
        result: ScoringResult = _scorer.score_detailed(payload)
        score = result.total_score
        reasons = result.strengths + result.risks
        st["scores"][vacancy.id] = result

        # Upsert into CRM with status="viewed" (won't downgrade an existing
        # higher-priority status such as "saved").
        try:
            _crm.upsert_job(
                vacancy_to_crm_job(vacancy, score, reasons, status="viewed")
            )
        except SheetsClientError as e:
            logger.warning("Failed to upsert viewed vacancy to CRM: %s", e)

        score_block = _format_score_block(result)
        if st.get("debug"):
            score_block += _format_debug_block(result)
        target = update.message if update.message else update.callback_query.message
        await target.reply_text(
            vacancy.short_text() + score_block,
            parse_mode=ParseMode.HTML,
            disable_web_page_preview=True,
            reply_markup=_buttons(vacancy.id),
        )
        return

    target = update.message if update.message else update.callback_query.message
    await target.reply_text("Новых вакансий нет. Попробуй позже: /jobs")


async def cmd_start(update: Update, _: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "\U0001f44b Привет! Команды:\n"
        "/jobs — следующая вакансия\n"
        "/next — пропустить\n"
        "/save — сохранить\n"
        "/hide — скрыть\n"
        "/coverletter — письмо\n"
        "/debug — вкл/выкл разбивку очков"
    )


async def cmd_debug(update: Update, _: ContextTypes.DEFAULT_TYPE) -> None:
    st = _state[update.effective_chat.id]
    st["debug"] = not st.get("debug", False)
    status = "включён \U0001f50d" if st["debug"] else "выключен"
    await update.message.reply_text(f"Debug-режим {status}")


async def cmd_jobs(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.effective_chat.id
    await update.message.chat.send_action("typing")
    try:
        await _show_next(update, chat_id, ctx)
    except HHClientError as e:
        logger.error(f"HH error: {e}")
        await update.message.reply_text(f"\u26a0\ufe0f Ошибка HH API: {e}")


async def cmd_next(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    await _show_next(update, update.effective_chat.id, ctx)


async def cmd_save(update: Update, _: ContextTypes.DEFAULT_TYPE) -> None:
    st = _state[update.effective_chat.id]
    cur = st.get("current")
    if not cur:
        await update.message.reply_text("Сначала открой вакансию: /jobs")
        return
    try:
        _crm.update_status(cur.id, "saved")
    except SheetsClientError as e:
        logger.warning("Failed to save status to CRM: %s", e)
    await update.message.reply_text("\U0001f4cc Сохранено")


async def cmd_hide(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    st = _state[update.effective_chat.id]
    cur = st.get("current")
    if cur:
        try:
            _crm.update_status(cur.id, "hidden")
        except SheetsClientError as e:
            logger.warning("Failed to hide vacancy in CRM: %s", e)
    await _show_next(update, update.effective_chat.id, ctx)


async def _generate_coverletter(chat_id: int) -> tuple:
    """Generate letter, return (cover_letter_text, vacancy_id)."""
    st = _state[chat_id]
    cur = st.get("current")
    if not cur:
        raise OpenAIClientError("Сначала открой вакансию: /jobs")

    scoring_result: ScoringResult | None = st["scores"].get(cur.id)

    full_description = cur.snippet_requirement or ""
    try:
        hh = HHClient()
        full_vacancy = await hh.get_vacancy(cur.id)
        desc_html = full_vacancy.get("description", "") or ""
        cleaned = _strip_html(desc_html)
        if cleaned:
            full_description = cleaned
    except HHClientError as e:
        logger.warning("Failed to fetch full vacancy %s: %s", cur.id, e)

    letter = await asyncio.to_thread(
        _openai.generate_cover_letter,
        vacancy_title=cur.name,
        company=cur.employer,
        requirements=full_description,
        user_profile=load_resume_context(),
        score=scoring_result.total_score if scoring_result else None,
        strengths=scoring_result.strengths if scoring_result else None,
        risks=scoring_result.risks if scoring_result else None,
    )
    return letter, cur.id or ""


async def _send_coverletter(chat_id: int, reply_fn) -> None:
    """Generate letter, send it, and save to CRM."""
    try:
        cover_letter, vacancy_id = await _generate_coverletter(chat_id)
    except OpenAIClientError as e:
        await reply_fn(f"\u26a0\ufe0f {e}")
        return

    await reply_fn(f"\u2709\ufe0f \u0421\u043e\u043f\u0440\u043e\u0432\u043e\u0434\u0438\u0442\u0435\u043b\u044c\u043d\u043e\u0435 \u043f\u0438\u0441\u044c\u043c\u043e:\n\n{cover_letter}")

    if vacancy_id:
        try:
            _crm.save_letter(vacancy_id, cover_letter)
        except SheetsClientError as e:
            logger.warning("Failed to save cover letter to CRM: %s", e)


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
        if vacancy_id:
            try:
                _crm.update_status(vacancy_id, "saved")
            except SheetsClientError as e:
                logger.warning("Failed to save vacancy in CRM: %s", e)
            await query.message.reply_text("\U0001f4cc Сохранено")
    elif action == "hide":
        if vacancy_id:
            try:
                _crm.update_status(vacancy_id, "hidden")
            except SheetsClientError as e:
                logger.warning("Failed to hide vacancy in CRM: %s", e)
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
    app.add_handler(CommandHandler("debug", cmd_debug))
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
