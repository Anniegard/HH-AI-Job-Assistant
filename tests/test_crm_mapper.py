import pytest

pytest.importorskip("pydantic")

from app.services.crm_mapper import CRM_HEADERS, vacancy_to_crm_row
from app.services.vacancy import Vacancy


def test_crm_headers_include_extended_schema() -> None:
    assert CRM_HEADERS == (
        "date",
        "vacancy",
        "company",
        "url",
        "score",
        "status",
        "reason",
        "cover_letter",
        "response",
        "published_at",
    )


def test_vacancy_to_crm_row_maps_all_fields() -> None:
    vacancy = Vacancy(
        id="1",
        name="Python Engineer",
        employer="ACME",
        url="https://hh.ru/v/1",
        published_at="2026-05-01T00:00:00+0300",
    )

    row = vacancy_to_crm_row(vacancy, score=88, reasons=["Python", "AI"], status="viewed")

    assert len(row) == 10
    assert row[1] == "Python Engineer"
    assert row[6] == "Python, AI"
    assert row[7] == ""
    assert row[8] == ""
    assert row[9] == "2026-05-01T00:00:00+0300"
