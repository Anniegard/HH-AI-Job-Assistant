"""Тесты парсинга вакансии (без сети)."""

from app.services.vacancy import Vacancy


SAMPLE_HH_ITEM = {
    "id": "12345",
    "name": "Python Developer (AI Automation)",
    "alternate_url": "https://hh.ru/vacancy/12345",
    "employer": {"name": "ACME AI"},
    "area": {"name": "Москва"},
    "salary": {"from": 200000, "to": 300000, "currency": "RUR", "gross": False},
    "schedule": {"name": "Удалённая работа"},
    "experience": {"name": "От 3 до 6 лет"},
    "snippet": {
        "requirement": "Опыт с <highlighttext>Python</highlighttext> и FastAPI",
        "responsibility": "Разработка AI ассистентов",
    },
    "published_at": "2025-05-01T10:00:00+0300",
}


def test_vacancy_from_hh_basic() -> None:
    v = Vacancy.from_hh(SAMPLE_HH_ITEM)
    assert v.id == "12345"
    assert v.name.startswith("Python Developer")
    assert v.employer == "ACME AI"
    assert v.area == "Москва"
    assert v.url == "https://hh.ru/vacancy/12345"
    assert v.salary is not None
    assert v.salary.from_ == 200000
    assert v.salary.to == 300000
    assert v.schedule == "Удалённая работа"


def test_vacancy_short_text_strips_highlight() -> None:
    v = Vacancy.from_hh(SAMPLE_HH_ITEM)
    text = v.short_text()
    assert "<highlighttext>" not in text
    assert "Python" in text
    assert "ACME AI" in text


def test_vacancy_handles_missing_salary() -> None:
    item = {**SAMPLE_HH_ITEM, "salary": None}
    v = Vacancy.from_hh(item)
    assert v.salary is None
    assert "💰" not in v.short_text()


def test_salary_format_only_from() -> None:
    item = {**SAMPLE_HH_ITEM, "salary": {"from": 150000, "to": None, "currency": "RUR"}}
    v = Vacancy.from_hh(item)
    assert v.salary is not None
    assert v.salary.format().startswith("от 150")
