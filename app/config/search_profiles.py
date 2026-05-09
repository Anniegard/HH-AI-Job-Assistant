"""Search profiles for Stage 4 daily workflow.

Each profile defines a HH API query and optional calibration hints.
The active profile is stored per-chat in bot state (in-memory).
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class SearchProfile:
    name: str
    display_name: str
    query: str
    area: int = 113  # 113 = Russia
    experience: str | None = None  # HH codes: noExperience|between1And3|between3And6|moreThan6
    keywords_boost: tuple[str, ...] = field(default_factory=tuple)
    penalties: tuple[str, ...] = field(default_factory=tuple)


PROFILES: dict[str, SearchProfile] = {
    "ai_builder": SearchProfile(
        name="ai_builder",
        display_name="AI Builder",
        query="AI builder автоматизация Python LLM FastAPI Telegram",
        keywords_boost=("AI agent", "automation", "FastAPI"),
        penalties=("sales", "1C"),
    ),
    "python_automation": SearchProfile(
        name="python_automation",
        display_name="Python Automation",
        query="Python автоматизация процессов API интеграция",
        keywords_boost=("Python", "автоматизация", "API"),
        penalties=("Java", "C++"),
    ),
    "ai_automation": SearchProfile(
        name="ai_automation",
        display_name="AI Automation",
        query="AI автоматизация LLM no-code workflow",
        keywords_boost=("AI автоматизация", "LLM", "no-code"),
    ),
    "fastapi_backend": SearchProfile(
        name="fastapi_backend",
        display_name="FastAPI Backend",
        query="FastAPI Python backend REST API",
        keywords_boost=("FastAPI", "REST API", "Python"),
        penalties=("frontend", "sales"),
    ),
    "llm_engineer": SearchProfile(
        name="llm_engineer",
        display_name="LLM Engineer",
        query="LLM engineer OpenAI GPT агент RAG",
        keywords_boost=("LLM", "OpenAI", "GPT", "Claude"),
    ),
    "ai_product_engineer": SearchProfile(
        name="ai_product_engineer",
        display_name="AI Product Engineer",
        query="AI product Python automation chatbot",
        keywords_boost=("AI product", "automation", "Python"),
    ),
}

DEFAULT_PROFILE_NAME = "ai_builder"


def get_profile(name: str) -> SearchProfile | None:
    return PROFILES.get(name)


def list_profiles() -> list[SearchProfile]:
    return list(PROFILES.values())
