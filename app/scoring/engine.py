"""Scoring Engine v3: Profile-based AI Automation scoring.

Scores vacancies against Denis's target profile:
  AI Automation / Python Automation / AI Builder / AI Tools Specialist.

Five independent components:
  role_fit:     0-35  -- title/description vs target roles
  task_fit:     0-30  -- tasks vs Denis's core activities
  stack_fit:    0-15  -- tech stack overlap
  growth_fit:   0-10  -- career growth in AI-automation direction
  risk_penalty: 0 to -40 -- mismatch signals (wrong stack, wrong role, etc.)

Total = role_fit + task_fit + stack_fit + growth_fit + risk_penalty, clamped [0, 100].

No hardcoded company names or specific vacancy titles.
Only universal signals based on role / task / stack / growth / risk.
"""

from __future__ import annotations

import functools
import re
from dataclasses import dataclass, field

_HTML_RE = re.compile(r"<[^>]+>")
_LONG_DASH_RE = re.compile(r"[—–]+")
_WS_RE = re.compile(r"\s+")


def normalize_text(text: str) -> str:
    """Normalize text for keyword matching (lowercase, strip HTML, etc.)."""
    if not text:
        return ""
    s = str(text).lower().replace("ё", "е")
    s = _HTML_RE.sub(" ", s)
    s = _LONG_DASH_RE.sub(" ", s)
    s = s.replace("-", " ")
    s = _WS_RE.sub(" ", s).strip()
    return s


_EXACT_MATCH_TERMS: frozenset[str] = frozenset(
    {
        "java", "ruby", "swift", "bot", "bots", "api", "ai", "ml", "nlp",
        "llm", "gpt", "mvp", "crm", "sdk", "bi", "make", "n8n", "go",
    }
)

_WB_L = r"(?<![a-zA-Zа-яёА-Яё0-9])"
_WB_R = r"(?![a-zA-Zа-яёА-Яё0-9])"


@functools.lru_cache(maxsize=1024)
def _compile_term(term: str) -> re.Pattern:
    escaped = re.escape(term)
    if term in _EXACT_MATCH_TERMS or (len(term) <= 4 and term.replace("+", "").isalpha()):
        return re.compile(_WB_L + escaped + _WB_R)
    return re.compile(_WB_L + escaped)


def _term_matches(text: str, term: str) -> bool:
    t = term.strip()
    if not t:
        return False
    return bool(_compile_term(t).search(text))


def _matches_any(text: str, patterns: tuple) -> bool:
    return any(_term_matches(text, p) for p in patterns)


@dataclass
class ScoringResult:
    """Structured result from ScoringEngine.score_detailed()."""

    total_score: int
    role_fit: int
    task_fit: int
    stack_fit: int
    growth_fit: int
    risk_penalty: int
    strengths: list = field(default_factory=list)
    risks: list = field(default_factory=list)
    recommendation: str = ""
    is_remote: bool = True
    # Per-component labels for debug output
    role_labels: list = field(default_factory=list)
    task_labels: list = field(default_factory=list)
    stack_labels: list = field(default_factory=list)
    growth_labels: list = field(default_factory=list)


Rule = tuple


ROLE_FIT_RULES = [
    (("ai автоматизац", "ai automation"), 25, "AI-автоматизации"),
    (("python automation",), 20, "Python Automation"),
    (("ai builder",), 20, "AI Builder"),
    (("ai agent developer",), 18, "AI Agent Developer"),
    (("chatbot developer", "bot developer", "бот разработч"), 15, "Bot/Chatbot Developer"),
    (("llm automation", "llm specialist"), 18, "LLM Specialist"),
    (("ai tools specialist", "ai tools developer"), 16, "AI Tools Specialist"),
    (("automation specialist", "automation engineer", "automation developer"), 18, "Automation Specialist"),
    (("специалист по автоматизац", "автоматизатор", "инженер автоматизац"), 12, "Специалист по автоматизации"),
    (("ai разработч", "ai engineer", "ai developer", "ai специалист"), 10, "AI Developer/Engineer"),
    (("ai ассистент", "ai assistant", "ai агент", "ai agent"), 8, "AI Agent/Assistant"),
    (("автоматизац",), 6, "автоматизация"),
    (("нейросет", "neural network"), 5, "нейросети"),
    (("llm", "large language model"), 4, "LLM"),
]
ROLE_FIT_MAX = 35

TASK_FIT_RULES = [
    (("автоматизац процесс", "автоматизировать процесс", "автоматизация бизнес"), 8, "автоматизация процессов"),
    (("автоматизац",), 4, "автоматизация"),
    (("автоматизир",), 4, "автоматизация"),
    (("telegram бот", "telegram bot", "телеграм бот", "чат бот", "chatbot", "чатбот"), 7, "Telegram-боты"),
    (("бот",), 3, "боты"),
    (("ai агент", "ai agent", "ai ассистент", "ai assistant"), 7, "AI-агенты/ассистенты"),
    (("api интегра", "api integration", "rest api", "апи интегра"), 5, "API-интеграции"),
    (("webhook",), 3, "webhook"),
    (("google sheets", "google таблиц", "sheets api"), 5, "Google Sheets"),
    (("excel автомат", "csv автомат", "таблиц автомат"), 3, "Excel/CSV автоматизация"),
    (("excel",), 3, "Excel"),
    (("внутренн инструмент", "внутренние инструмент", "внутренних инструмент", "internal tool"), 5, "внутренние инструменты"),
    (("mvp", "прототип"), 4, "MVP/прототипы"),
    (("автоворонк",), 5, "автоворонки"),
    (("генерац контента", "генератор контента", "контент генерац"), 4, "генерация контента"),
    (("аналитика эффективност",), 4, "аналитика эффективности"),
    (("интеграц",), 2, "интеграции"),
    (("база знани", "knowledge base"), 3, "база знаний"),
]
TASK_FIT_MAX = 30

STACK_FIT_RULES = [
    (("python",), 5, "Python"),
    (("fastapi",), 3, "FastAPI"),
    (("rest api",), 2, "REST API"),
    (("webhook",), 2, "webhook"),
    (("telegram",), 2, "Telegram"),
    (("google sheets api", "google таблиц", "sheets api"), 2, "Google Sheets API"),
    (("openai", "chatgpt"), 3, "OpenAI/ChatGPT"),
    (("claude",), 2, "Claude"),
    (("gemini",), 2, "Gemini"),
    (("n8n",), 3, "n8n"),
    (("make.com", "make automati", "make интегра"), 2, "Make"),
    (("zapier",), 2, "Zapier"),
    (("airtable",), 2, "Airtable"),
    (("notion",), 1, "Notion"),
    (("github",), 1, "GitHub"),
    (("ubuntu",), 1, "Ubuntu VM"),
    (("no code", "low code", "nocode", "lowcode"), 3, "no-code/low-code"),
]
STACK_FIT_MAX = 15

GROWTH_FIT_RULES = [
    (("ai направлен", "развитие ai", "развития ai"), 3, "развитие AI-направления"),
    (("внутренн ai", "internal ai", "ai инструмент"), 3, "внутренние AI-инструменты"),
    (("продуктов задач", "продуктов разработк", "продуктов подход"), 2, "продуктовые задачи"),
    (("гипотез",), 2, "работа с гипотезами"),
    (("влиять на процесс", "формировать процесс", "предлагать решени"), 2, "влияние на процессы"),
    (("реальн внедрен", "реальные проект"), 2, "реальные внедрения"),
    (("внутренние проект", "внутренних проект"), 2, "внутренние проекты"),
]
GROWTH_FIT_MAX = 10

RISK_RULES = [
    (("java", "spring boot", "spring framework", "kotlin developer"), -15, "Java/Kotlin стек"),
    (("c++", "cpp", "qt developer", "qt framework"), -15, "C++ стек"),
    (("1с ", "1c ", "1с разработ", "1с программист", "1с бухгалтер", "1с специалист"), -20, "1С стек"),
    ((".net ", "c# developer", "c sharp", "asp.net"), -10, ".NET стек"),
    (("ruby on rails", "ruby разработ", "ruby developer"), -10, "Ruby стек"),
    (("ios developer", "swift разработ", "swift developer"), -10, "iOS/Swift стек"),
    (("android developer", "android разработ"), -10, "Android стек"),
    (("аккаунт менеджер", "account manager"), -15, "Sales/Account Manager"),
    (("sales manager", "менеджер по продажам", "руководитель отдела продаж"), -15, "Sales Manager"),
    (("devops engineer", "sre engineer", "kubernetes administrator", "site reliability"), -15, "DevOps-only роль"),
    (("frontend разработчик", "react developer", "vue developer", "верстальщик", "frontend developer"), -15, "Frontend-only роль"),
    (("бухгалтер", "финансовый аналитик"), -15, "роль не по профилю"),
    (("pytorch", "tensorflow", "deep learning", "computer vision"), -8, "Deep Learning без automation"),
    (("ml engineer", "machine learning engineer", "data scientist"), -8, "ML/DS роль без automation"),
    (("nlp research", "research engineer", "research scientist"), -12, "NLP Research без automation"),
    (("team lead", "тимлид", "tech lead", "руководитель команды", "руководитель разработки"), -10, "Team Lead роль"),
    (("руководитель группы", "руководитель отдела разработ"), -8, "руководящая роль"),
]

RISK_PENALTY_MAX = -40

_SENIOR_ONLY_PATTERNS = (
    "senior", "от 5 лет", "5+ лет", "более 5 лет", "от пяти лет",
)

_ML_SKIP_LABELS = frozenset(
    {"Deep Learning без automation", "ML/DS роль без automation", "NLP Research без automation"}
)

_REMOTE_SIGNALS = ("удален", "remote", "дистанционн", "гибрид")


def _is_remote_vacancy(text: str, schedule_raw) -> bool:
    if schedule_raw:
        sched = normalize_text(str(schedule_raw))
        if any(sig in sched for sig in _REMOTE_SIGNALS):
            return True
    return any(sig in text for sig in _REMOTE_SIGNALS)


def _score_component(text: str, rules: list, cap: int):
    total = 0
    labels = []
    seen = set()
    for patterns, points, label in rules:
        if _matches_any(text, patterns):
            total += points
            if label not in seen:
                labels.append(label)
                seen.add(label)
    return min(max(total, 0), cap), labels


def _score_risks(text: str, has_strong_ai: bool):
    total = 0
    labels = []
    seen = set()

    for patterns, points, label in RISK_RULES:
        if has_strong_ai and label in _ML_SKIP_LABELS:
            continue
        if has_strong_ai and label in ("Team Lead роль", "руководящая роль"):
            continue
        if _matches_any(text, patterns):
            total += points
            if label not in seen:
                labels.append(label)
                seen.add(label)

    if not has_strong_ai and _matches_any(text, _SENIOR_ONLY_PATTERNS) and "Team Lead роль" not in seen:
        total -= 10
        labels.append("senior без AI automation")

    return max(total, RISK_PENALTY_MAX), labels


def _build_recommendation(score: int) -> str:
    if score >= 80:
        return "Сильный матч. Рекомендую откликаться уверенно."
    if score >= 60:
        return "Хороший матч. Стоит рассмотреть."
    if score >= 40:
        return "Средний матч. Можно попробовать с осторожным письмом."
    return "Слабый матч. Не приоритет."


class ScoringEngine:
    """Profile-based scoring engine v3 for AI Automation roles."""

    def _build_text(self, vacancy: dict):
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
        text = normalize_text(" ".join(str(p) for p in parts))
        schedule_raw = vacancy.get("schedule") or None
        return text, schedule_raw

    def score_detailed(self, vacancy: dict) -> ScoringResult:
        """Score vacancy and return structured ScoringResult."""
        text, schedule_raw = self._build_text(vacancy)

        role_score, role_labels = _score_component(text, ROLE_FIT_RULES, ROLE_FIT_MAX)
        task_score, task_labels = _score_component(text, TASK_FIT_RULES, TASK_FIT_MAX)
        stack_score, stack_labels = _score_component(text, STACK_FIT_RULES, STACK_FIT_MAX)
        growth_score, growth_labels = _score_component(text, GROWTH_FIT_RULES, GROWTH_FIT_MAX)

        has_strong_ai = role_score >= 15 or task_score >= 10

        risk_score, risk_labels = _score_risks(text, has_strong_ai)

        is_remote = _is_remote_vacancy(text, schedule_raw)
        if not is_remote and "офис" in text:
            risk_score = max(risk_score - 5, RISK_PENALTY_MAX)
            if "офис-only" not in risk_labels:
                risk_labels.append("офис-only")

        positive = role_score + task_score + stack_score + growth_score
        total = max(0, min(100, positive + risk_score))

        strengths = []
        seen_s = set()
        for lbl in role_labels + task_labels + stack_labels + growth_labels:
            if lbl not in seen_s:
                strengths.append(lbl)
                seen_s.add(lbl)

        return ScoringResult(
            total_score=total,
            role_fit=role_score,
            task_fit=task_score,
            stack_fit=stack_score,
            growth_fit=growth_score,
            risk_penalty=risk_score,
            strengths=strengths,
            risks=risk_labels,
            recommendation=_build_recommendation(total),
            is_remote=is_remote,
            role_labels=role_labels,
            task_labels=task_labels,
            stack_labels=stack_labels,
            growth_labels=growth_labels,
        )

    def score(self, vacancy: dict) -> tuple:
        """Backward-compatible interface: (total_score, unique_reasons).

        Use score_detailed() for the full structured result.
        """
        result = self.score_detailed(vacancy)
        reasons = []
        seen = set()
        for r in result.strengths + result.risks:
            if r not in seen:
                reasons.append(r)
                seen.add(r)
        return result.total_score, reasons
