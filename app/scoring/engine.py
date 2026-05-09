"""Scoring Engine - v2: AI Automation focus.

Rule-based 0-100 scoring tuned for AI Automation / AI Builder /
AI Content Automation roles. Detects Russian and English keywords
in the vacancy text (name, employer, snippets, full description,
schedule, experience, area), normalizes the text (lowercase, yo->e,
strip HTML, collapse dashes/whitespace), and returns Russian reasons.

The score is decomposed into five categories:

* A. Target role match            - up to 30 points
* B. Technical implementation     - up to 30 points
* C. Product / content packaging  - up to 20 points
* D. Working conditions / fit     - up to 10 points
* E. Penalties (mismatch signals) - up to -35 points

Final score is clamped to [0, 100].
"""

from __future__ import annotations

import re

# --------------------------------------------------------------------------- #
# Text normalization
# --------------------------------------------------------------------------- #

_HTML_RE = re.compile(r"<[^>]+>")
_LONG_DASH_RE = re.compile(r"[—–]+")
_WS_RE = re.compile(r"\s+")


def normalize_text(text: str) -> str:
    """Normalize text for keyword matching."""
    if not text:
        return ""
    s = str(text).lower().replace("ё", "е")  # yo -> e
    s = _HTML_RE.sub(" ", s)
    s = _LONG_DASH_RE.sub(" ", s)
    s = s.replace("-", " ")
    s = _WS_RE.sub(" ", s).strip()
    return s


Rule = tuple[tuple[str, ...], int, str]


CATEGORY_A_RULES: list[Rule] = [
    (("ai автоматизац", "ai automation", "ии автоматизац"), 14, "AI-автоматизации"),
    (("автоматизац", "automation"), 6, "автоматизация процессов"),
    (("ai агент", "ai agents", "ai assistant"), 10, "AI-агенты/ассистенты"),
    (("ассистент",), 6, "AI-агенты/ассистенты"),
    (("нейросет",), 8, "нейросети/LLM"),
    (("llm", "large language"), 5, "нейросети/LLM"),
    (("ai builder", "ai tools", "ai инструмент"), 6, "AI-инструменты"),
    (("чат бот", "чатбот", "chatbot", "telegram бот", "тг бот"), 6, "боты/AI-ассистенты"),
    (("боты", "бота", "ботов", "ботом", "ботам", "бот ", " бот.", "bots", " bot ", " bot.", " bot,"), 5, "боты/AI-ассистенты"),
]
CATEGORY_A_MAX = 30


CATEGORY_B_RULES: list[Rule] = [
    (("python",), 6, "Python/API/интеграции"),
    (("fastapi",), 4, "Python/API/интеграции"),
    (("rest api", "api интегра", " api ", " api,", " api.", "openapi", "веб api"), 4, "Python/API/интеграции"),
    (("webhook",), 3, "Python/API/интеграции"),
    (("интеграц", "integration"), 4, "Python/API/интеграции"),
    (("telegram",), 3, "Telegram"),
    (("google sheets", "google таблиц", "sheets api"), 4, "Google Sheets"),
    (("openai", "chatgpt", "gpt 4", "gpt 3"), 4, "OpenAI/ChatGPT"),
    (("claude",), 2, "Claude/Gemini"),
    (("gemini",), 2, "Claude/Gemini"),
    (("n8n", "make.com", " make ", "zapier"), 5, "n8n/Make/Zapier"),
    (("airtable", "notion"), 3, "Airtable/Notion"),
    (("low code", "no code"), 6, "no-code/low-code"),
    (("автоворонк",), 5, "автоворонки"),
    (("генератор контента", "генерация контента", "контент генерац"), 4, "генерация контента"),
]
CATEGORY_B_MAX = 30


CATEGORY_C_RULES: list[Rule] = [
    (("mvp", "быстр прототип", "быстрые прототип", "прототипиров"), 3, "MVP/быстрые прототипы"),
    (("гипотез",), 3, "продуктовые гипотезы"),
    (("сценари",), 3, "пользовательские сценарии"),
    (("инструкц",), 3, "контентная упаковка"),
    (("гайд",), 3, "контентная упаковка"),
    (("кейс",), 3, "контентная упаковка"),
    (("презентац", "описание продукт"), 2, "контентная упаковка"),
    (("шаблон",), 2, "контентная упаковка"),
    (("контент",), 3, "контентная упаковка"),
    (("маркетинг",), 2, "контент/маркетинг"),
    (("продукт",), 2, "продуктовая работа"),
    (("база промпт", "промпт"), 3, "промпт-инжиниринг"),
    (("аналитика эффективност",), 3, "аналитика эффективности"),
    (("база знани", "базы знани", "базе знани", "базу знани", "баз знаний", "knowledge base"), 3, "база знаний"),
]
CATEGORY_C_MAX = 20


CATEGORY_D_RULES: list[Rule] = [
    (("удаленн", "удален ", "удален.", "удален,", "remote", "дистанционн"), 4, "удалёнка"),
    (("гибрид",), 3, "гибрид"),
    (("junior", "джуниор"), 2, "junior/middle"),
    (("middle", "мидл"), 2, "junior/middle"),
    (("внутренн проект", "внутренние проект", "внутренних проект", "внутренних инструмент", "внутренних задач", "внутренние инструмент", "internal tool", "internal project"), 3, "внутренние проекты"),
    (("ai направлен", "развитие ai", "развития ai", "развивать ai"), 4, "развитие AI-направления"),
]
CATEGORY_D_MAX = 10


PENALTY_RULES: list[tuple[tuple[str, ...], int, str]] = [
    (("senior java", "java backend", "java developer", "разработчик java", " java ", " java,", " java.", "spring boot", "kotlin developer"), -15, "Java/Kotlin стек"),
    ((" c++ ", " c++,", " c++.", " cpp ", "qt developer"), -15, "C++ стек"),
    ((" 1с ", " 1c ", "1с разработ", "1с программист", "1с бухгалтер"), -20, "1С стек"),
    ((" .net ", "c# developer", "c sharp"), -10, ".NET стек"),
    (("ruby on rails", " ruby ", "ruby разработ"), -10, "Ruby стек"),
    (("ios developer", "swift разработ"), -10, "iOS/Swift стек"),
    (("android developer",), -10, "Android стек"),
    (("аккаунт менеджер", "account manager"), -10, "роль не про AI automation"),
    (("sales manager", "продажи b2b", "руководитель отдела продаж", "менеджер по продажам"), -10, "роль не про AI automation"),
    (("devops engineer", "sre engineer", "kubernetes administrator"), -10, "DevOps-only роль"),
    (("frontend разработчик", "react developer", "vue developer", "верстальщик"), -10, "Frontend-only роль"),
    (("бухгалтер", "финансовый аналитик"), -15, "роль не по профилю"),
    (("pytorch", "tensorflow", "deep learning", "computer vision", "ml engineer", "data scientist"), -8, "глубокое ML/DS без automation"),
]


SENIOR_PATTERNS: tuple[str, ...] = (
    "senior",
    "тимлид",
    "team lead",
    "tech lead",
    "от 5 лет",
    "5+ лет",
    "более 5 лет",
    "от пяти лет",
)


def _matches_any(text: str, patterns: tuple[str, ...]) -> bool:
    return any(p in text for p in patterns)


def _category_score(text: str, rules: list[Rule], cap: int) -> tuple[int, list[str]]:
    score = 0
    reasons: list[str] = []
    seen: set[str] = set()
    for patterns, points, label in rules:
        if _matches_any(text, patterns):
            score += points
            if label not in seen:
                reasons.append(label)
                seen.add(label)
    return min(score, cap), reasons


def _strip_html(text: str) -> str:
    if not text:
        return ""
    return _WS_RE.sub(" ", _HTML_RE.sub(" ", text)).strip()


class ScoringEngine:
    """Rule-based scoring (0-100) tuned for AI automation roles."""

    def score(self, vacancy: dict) -> tuple[int, list[str]]:
        parts = [
            vacancy.get("name", "") or "",
            vacancy.get("employer", "") or "",
            vacancy.get("snippet_requirement", "") or "",
            vacancy.get("snippet_responsibility", "") or "",
            vacancy.get("description", "") or "",
            vacancy.get("schedule", "") or "",
            vacancy.get("experience", "") or "",
            vacancy.get("area", "") or "",
        ]
        text = " " + normalize_text(" ".join(str(p) for p in parts)) + " "

        a_score, a_reasons = _category_score(text, CATEGORY_A_RULES, CATEGORY_A_MAX)
        b_score, b_reasons = _category_score(text, CATEGORY_B_RULES, CATEGORY_B_MAX)
        c_score, c_reasons = _category_score(text, CATEGORY_C_RULES, CATEGORY_C_MAX)
        d_score, d_reasons = _category_score(text, CATEGORY_D_RULES, CATEGORY_D_MAX)

        positive_total = a_score + b_score + c_score + d_score

        penalty_total = 0
        penalty_reasons: list[str] = []
        seen_pen: set[str] = set()

        ai_automation_strong = "AI-автоматизации" in a_reasons
        bots_signal = "боты/AI-ассистенты" in a_reasons
        has_automation_or_bots = ai_automation_strong or bots_signal or b_score >= 10

        for patterns, points, label in PENALTY_RULES:
            if "ML/DS" in label and has_automation_or_bots:
                continue
            if _matches_any(text, patterns):
                penalty_total += points
                if label not in seen_pen:
                    penalty_reasons.append(label)
                    seen_pen.add(label)

        if _matches_any(text, SENIOR_PATTERNS) and not ai_automation_strong:
            penalty_total -= 10
            penalty_reasons.append("senior без AI automation")

        text_has_office = "офис" in text and not _matches_any(
            text,
            ("удаленн", "удален ", "remote", "гибрид", "дистанционн"),
        )
        if text_has_office:
            penalty_total -= 5
            penalty_reasons.append("офис-only")

        penalty_total = max(penalty_total, -35)

        final = positive_total + penalty_total
        final = max(0, min(100, final))

        ordered = a_reasons + b_reasons + c_reasons + d_reasons + penalty_reasons
        seen_r: set[str] = set()
        unique_reasons: list[str] = []
        for r in ordered:
            if r not in seen_r:
                unique_reasons.append(r)
                seen_r.add(r)

        return final, unique_reasons
