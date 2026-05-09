from __future__ import annotations

import asyncio
import re
from collections import defaultdict
from dataclasses import replace as dc_replace
from datetime import datetime, timezone

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.constants import ParseMode
from telegram.ext import (
    Application,
    ApplicationBuilder,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
)

from app.config.search_profiles import (
    DEFAULT_PROFILE_NAME,
    PROFILES,
    SearchProfile,
    get_profile,
    list_profiles,
)
from app.core.config import settings
from app.core.logging import logger
from app.core.resume import load_resume_context
from app.scoring.calibration import calibrate
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

DAILY_TOP_N = 5
DAILY_PER_PAGE = 50


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
        # Stage 4 additions
        "active_profile": DEFAULT_PROFILE_NAME,
        "vacancy_cache": {},  # {vacancy_id: Vacancy} — lookup for /daily letter generation
    }


_state: dict[int, dict] = defaultdict(_new_state)
_scorer = ScoringEngine()
_crm = JobCRM()
_openai = OpenAIClient()


# ---------------------------------------------------------------------------
# Button builders
# ---------------------------------------------------------------------------


def _buttons(vacancy_id: str) -> InlineKeyboardMarkup:
    """Buttons for /jobs single-vacancy view."""
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


def _daily_buttons(vacancy_id: str) -> InlineKeyboardMarkup:
    """Compact buttons for /daily digest cards — no [Далее], letter embeds vacancy_id."""
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    "\U0001f4cc Сохранить", callback_data=f"save:{vacancy_id}"
                ),
                InlineKeyboardButton(
                    "\U0001f44e Скрыть", callback_data=f"hide:{vacancy_id}"
                ),
                InlineKeyboardButton(
                    "✉ Письмо", callback_data=f"coverletter:{vacancy_id}"
                ),
            ]
        ]
    )


# ---------------------------------------------------------------------------
# Queue and scoring helpers
# ---------------------------------------------------------------------------


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


def _build_fast_payload(vacancy: Vacancy) -> dict:
    """Snippet-only scoring payload — no extra HH API call. Used by /daily for speed."""
    return vacancy.model_dump()


# ---------------------------------------------------------------------------
# Formatting helpers
# ---------------------------------------------------------------------------


def _format_score_block(result: ScoringResult) -> str:
    """Format the scoring block for Telegram display."""
    lines: list[str] = []
    lines.append(f"\n\n\U0001f3af <b>Оценка: {result.total_score}/100</b>")

    if not result.is_remote:
        lines.append("⚠️ <b>Формат: офис</b> (не удалённая/гибридная)")

    if result.strengths:
        top = ", ".join(result.strengths[:4])
        lines.append(f"✅ Совпадения: {top}")

    if result.risks:
        top_risks = ", ".join(result.risks[:3])
        lines.append(f"⚠️ Риски: {top_risks}")

    return "\n".join(lines)


def _format_debug_block(result: ScoringResult) -> str:
    """Format detailed per-component score breakdown for debug mode."""
    from app.scoring.engine import GROWTH_FIT_MAX, ROLE_FIT_MAX, STACK_FIT_MAX, TASK_FIT_MAX

    def _labels(lst: list) -> str:
        return ", ".join(lst) if lst else "—"

    lines = ["\n\n\U0001f50d <b>Debug: разбивка очков</b>"]
    lines.append(
        f"  role   {result.role_fit:>3}/{ROLE_FIT_MAX}  "
        f"→ {_labels(result.role_labels)}"
    )
    lines.append(
        f"  task   {result.task_fit:>3}/{TASK_FIT_MAX}  "
        f"→ {_labels(result.task_labels)}"
    )
    lines.append(
        f"  stack  {result.stack_fit:>3}/{STACK_FIT_MAX}  "
        f"→ {_labels(result.stack_labels)}"
    )
    lines.append(
        f"  growth {result.growth_fit:>3}/{GROWTH_FIT_MAX}  "
        f"→ {_labels(result.growth_labels)}"
    )
    risk_str = _labels(result.risks) if result.risks else "—"
    lines.append(f"  risk   {result.risk_penalty:>4}     → {risk_str}")
    lines.append(f"  <b>итого  {result.total_score:>3}/100</b>")
    lines.append(f"  {result.recommendation}")
    return "\n".join(lines)


def _format_daily_card(n: int, vacancy: Vacancy, result: ScoringResult) -> str:
    """Compact card format for /daily digest."""
    lines = [
        f"<b>#{n} {vacancy.name}</b>",
        f"Компания: {vacancy.employer}",
        f"Оценка: {result.total_score}",
    ]
    if not result.is_remote:
        lines.append("⚠️ офис")
    for s in result.strengths[:2]:
        lines.append(f"+ {s}")
    for r in result.risks[:1]:
        lines.append(f"- {r}")
    lines.append(f"\U0001f517 {vacancy.url}")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Core bot flow
# ---------------------------------------------------------------------------


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


# ---------------------------------------------------------------------------
# Cover letter generation
# ---------------------------------------------------------------------------


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
        await reply_fn(f"⚠️ {e}")
        return

    await reply_fn(
        f"✉️ Сопроводительное письмо:\n\n{cover_letter}"
    )

    if vacancy_id:
        try:
            _crm.save_letter(vacancy_id, cover_letter)
        except SheetsClientError as e:
            logger.warning("Failed to save cover letter to CRM: %s", e)


async def _send_coverletter_by_id(chat_id: int, vacancy_id: str, reply_fn) -> None:
    """Generate letter for a specific vacancy_id — used by /daily cards."""
    st = _state[chat_id]
    vacancy = st["vacancy_cache"].get(vacancy_id)
    if not vacancy:
        await reply_fn(
            "⚠️ Вакансия не найдена в кэше сессии. Попробуй /daily снова."
        )
        return
    original_current = st["current"]
    st["current"] = vacancy
    try:
        await _send_coverletter(chat_id, reply_fn)
    finally:
        st["current"] = original_current


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------


async def cmd_start(update: Update, _: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "\U0001f44b Привет! Команды:\n"
        "/daily — топ-5 вакансий за сегодня\n"
        "/jobs — следующая вакансия\n"
        "/next — пропустить\n"
        "/save — сохранить\n"
        "/hide — скрыть\n"
        "/coverletter — письмо\n"
        "/profiles — профили поиска\n"
        "/profile &lt;name&gt; — сменить профиль\n"
        "/stats — статистика CRM\n"
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
        await update.message.reply_text(f"⚠️ Ошибка HH API: {e}")


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


async def cmd_coverletter(update: Update, _: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.effective_chat.id
    await _send_coverletter(chat_id, update.message.reply_text)


async def cmd_daily(update: Update, _: ContextTypes.DEFAULT_TYPE) -> None:
    """Fetch top-N vacancies for today using the active search profile."""
    chat_id = update.effective_chat.id
    st = _state[chat_id]
    await update.message.chat.send_action("typing")

    # Load CRM once per session
    if not st["crm_loaded"]:
        try:
            _crm.load_jobs()
        except SheetsClientError as e:
            logger.warning("Failed to preload CRM for /daily: %s", e)
        st["crm_loaded"] = True

    profile: SearchProfile = get_profile(st["active_profile"]) or get_profile(
        DEFAULT_PROFILE_NAME
    )
    now_iso = datetime.now(timezone.utc).isoformat()

    # Fetch candidates from HH
    try:
        client = HHClient()
        raw = await client.search_vacancies(
            text=profile.query,
            area=profile.area,
            per_page=DAILY_PER_PAGE,
            page=0,
            **({"experience": profile.experience} if profile.experience else {}),
        )
    except HHClientError as e:
        logger.error("HH error in /daily: %s", e)
        await update.message.reply_text(f"⚠️ Ошибка HH API: {e}")
        return

    vacancies = [Vacancy.from_hh(item) for item in raw.get("items", [])]

    # Filter: skip session-seen and CRM-hidden/applied/rejected
    candidates = [
        v
        for v in vacancies
        if v.id not in st["seen"] and not _crm.should_skip(v.id)
    ]

    if not candidates:
        await update.message.reply_text(
            "Новых вакансий не найдено. Попробуй другой профиль: /profiles"
        )
        return

    # Score all candidates (fast, snippet-only — no extra HH API calls)
    scored: list[tuple[Vacancy, ScoringResult]] = []
    for v in candidates:
        payload = _build_fast_payload(v)
        result = _scorer.score_detailed(payload)
        # Apply calibration layer on top of base score
        text_for_calibration = " ".join(
            [v.name or "", v.snippet_requirement or "", v.snippet_responsibility or ""]
        )
        calibrated_score = calibrate(result.total_score, text_for_calibration)
        result = dc_replace(result, total_score=calibrated_score)
        scored.append((v, result))

    # Sort by calibrated score DESC, keep top-N
    scored.sort(key=lambda x: x[1].total_score, reverse=True)
    top = scored[:DAILY_TOP_N]

    # Upsert to CRM, populate session cache
    for v, result in top:
        st["seen"].add(v.id)
        st["vacancy_cache"][v.id] = v
        st["scores"][v.id] = result
        try:
            _crm.upsert_job(
                vacancy_to_crm_job(
                    v,
                    result.total_score,
                    result.strengths + result.risks,
                    status="viewed",
                    profile=profile.name,
                    last_seen_at=now_iso,
                )
            )
        except SheetsClientError as e:
            logger.warning("Failed to upsert daily vacancy %s: %s", v.id, e)

    # Header message
    await update.message.reply_text(
        f"\U0001f4cb <b>Дейли-дайджест — {profile.display_name}</b>\n"
        f"Топ {len(top)} из {len(candidates)} новых вакансий",
        parse_mode=ParseMode.HTML,
    )

    # One compact card per vacancy
    for n, (v, result) in enumerate(top, start=1):
        card_text = _format_daily_card(n, v, result)
        await update.message.reply_text(
            card_text,
            parse_mode=ParseMode.HTML,
            disable_web_page_preview=True,
            reply_markup=_daily_buttons(v.id),
        )


async def cmd_profiles(update: Update, _: ContextTypes.DEFAULT_TYPE) -> None:
    """List all available search profiles."""
    st = _state[update.effective_chat.id]
    current = st["active_profile"]
    lines = ["<b>Профили поиска:</b>"]
    for p in list_profiles():
        marker = "✅" if p.name == current else "  "
        lines.append(f"{marker} <code>{p.name}</code> — {p.display_name}")
    lines.append("\nСменить: /profile &lt;name&gt;")
    await update.message.reply_text("\n".join(lines), parse_mode=ParseMode.HTML)


async def cmd_profile(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    """Switch active search profile: /profile <name>"""
    chat_id = update.effective_chat.id
    args = ctx.args
    if not args:
        await update.message.reply_text(
            "Укажи имя профиля: /profile ai_builder\nСмотри список: /profiles"
        )
        return
    name = args[0].strip().lower()
    profile = get_profile(name)
    if profile is None:
        known = ", ".join(PROFILES.keys())
        await update.message.reply_text(
            f"Профиль «{name}» не найден.\nДоступные: {known}"
        )
        return
    _state[chat_id]["active_profile"] = name
    await update.message.reply_text(
        f"✅ Активный профиль: <b>{profile.display_name}</b>\n"
        f"Запрос: <code>{profile.query}</code>",
        parse_mode=ParseMode.HTML,
    )


async def cmd_stats(update: Update, _: ContextTypes.DEFAULT_TYPE) -> None:
    """Show CRM statistics derived from sheet data."""
    await update.message.chat.send_action("typing")
    try:
        jobs = _crm.load_jobs()
    except SheetsClientError as e:
        await update.message.reply_text(f"⚠️ Ошибка чтения CRM: {e}")
        return

    total = len(jobs)
    by_status: dict[str, int] = {}
    by_profile: dict[str, int] = {}
    for job in jobs:
        status = job.get("status", "unknown")
        by_status[status] = by_status.get(status, 0) + 1
        prof = job.get("profile") or "unknown"
        by_profile[prof] = by_profile.get(prof, 0) + 1

    saved = by_status.get("saved", 0)
    hidden = by_status.get("hidden", 0)
    letters = by_status.get("letter_generated", 0)
    viewed = by_status.get("viewed", 0)
    applied = by_status.get("applied", 0)

    lines = [f"<b>\U0001f4ca Статистика CRM ({total} вакансий)</b>", ""]
    lines.append(f"\U0001f441 Просмотрено:   {viewed}")
    lines.append(f"\U0001f4cc Сохранено:     {saved}")
    lines.append(f"✉ Письма:        {letters}")
    lines.append(f"✅ Откликнулся:   {applied}")
    lines.append(f"\U0001f44e Скрыто:        {hidden}")

    if by_profile:
        lines.append("\n<b>По профилям:</b>")
        for p_name, count in sorted(by_profile.items(), key=lambda x: -x[1]):
            display = (
                PROFILES[p_name].display_name if p_name in PROFILES else p_name
            )
            lines.append(f"  {display}: {count}")

    await update.message.reply_text("\n".join(lines), parse_mode=ParseMode.HTML)


# ---------------------------------------------------------------------------
# Callback query handler
# ---------------------------------------------------------------------------


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
        if vacancy_id:
            # /daily path: vacancy_id embedded in callback_data
            await _send_coverletter_by_id(
                update.effective_chat.id, vacancy_id, query.message.reply_text
            )
        else:
            # /jobs path: legacy, uses st["current"]
            await _send_coverletter(update.effective_chat.id, query.message.reply_text)


# ---------------------------------------------------------------------------
# Application factory and entry point
# ---------------------------------------------------------------------------


def build_app() -> Application:
    if not settings.telegram_token:
        raise RuntimeError("TELEGRAM_TOKEN not set. Fill .env (see .env.example).")

    app = ApplicationBuilder().token(settings.telegram_token).build()
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("daily", cmd_daily))
    app.add_handler(CommandHandler("jobs", cmd_jobs))
    app.add_handler(CommandHandler("next", cmd_next))
    app.add_handler(CommandHandler("save", cmd_save))
    app.add_handler(CommandHandler("hide", cmd_hide))
    app.add_handler(CommandHandler("coverletter", cmd_coverletter))
    app.add_handler(CommandHandler("profiles", cmd_profiles))
    app.add_handler(CommandHandler("profile", cmd_profile))
    app.add_handler(CommandHandler("stats", cmd_stats))
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
