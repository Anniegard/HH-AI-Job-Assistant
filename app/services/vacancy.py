"""Модели данных для вакансий."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class Salary(BaseModel):
    """Зарплата (любое поле может быть None)."""

    from_: int | None = Field(default=None, alias="from")
    to: int | None = None
    currency: str | None = None
    gross: bool | None = None

    model_config = {"populate_by_name": True}

    def format(self) -> str:
        if self.from_ is None and self.to is None:
            return "не указана"
        cur = self.currency or ""
        if self.from_ and self.to:
            return f"{self.from_:,}–{self.to:,} {cur}".replace(",", " ")
        if self.from_:
            return f"от {self.from_:,} {cur}".replace(",", " ")
        return f"до {self.to:,} {cur}".replace(",", " ")


class Vacancy(BaseModel):
    """Упрощённая вакансия после парсинга ответа HH."""

    id: str
    name: str
    employer: str
    url: str
    area: str | None = None
    salary: Salary | None = None
    schedule: str | None = None
    experience: str | None = None
    snippet_requirement: str | None = None
    snippet_responsibility: str | None = None
    published_at: str | None = None

    @classmethod
    def from_hh(cls, raw: dict[str, Any]) -> "Vacancy":
        """Парсинг одного элемента из items[] ответа /vacancies."""
        snippet = raw.get("snippet") or {}
        salary_raw = raw.get("salary")
        return cls(
            id=str(raw["id"]),
            name=raw.get("name", ""),
            employer=(raw.get("employer") or {}).get("name", ""),
            url=raw.get("alternate_url") or raw.get("url", ""),
            area=(raw.get("area") or {}).get("name"),
            salary=Salary.model_validate(salary_raw) if salary_raw else None,
            schedule=(raw.get("schedule") or {}).get("name"),
            experience=(raw.get("experience") or {}).get("name"),
            snippet_requirement=snippet.get("requirement"),
            snippet_responsibility=snippet.get("responsibility"),
            published_at=raw.get("published_at"),
        )

    def short_text(self) -> str:
        """Короткое представление для Telegram (HTML)."""
        lines = [
            f"<b>{self.name}</b>",
            f"🏢 {self.employer}" + (f" · {self.area}" if self.area else ""),
        ]
        if self.salary:
            lines.append(f"💰 {self.salary.format()}")
        if self.schedule:
            lines.append(f"🕒 {self.schedule}")
        if self.experience:
            lines.append(f"📌 опыт: {self.experience}")
        if self.snippet_requirement:
            lines.append(f"\n<i>{_clean(self.snippet_requirement)}</i>")
        lines.append(f"\n🔗 {self.url}")
        return "\n".join(lines)


def _clean(text: str) -> str:
    """HH присылает highlight-теги <highlighttext>; убираем их."""
    return text.replace("<highlighttext>", "").replace("</highlighttext>", "")
