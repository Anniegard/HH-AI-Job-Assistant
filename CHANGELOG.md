# Changelog

All notable changes to this project will be documented in this file.

---

## [unreleased] — 2026-05-08

### Stage 1 — Foundation

- `app/core/config.py` — добавлены `hh_base_url`, `hh_user_agent`, `extra="ignore"`
- `app/core/logging.py` — настроен loguru с цветным форматом
- `app/services/hh_client.py` — асинхронный httpx клиент для HH API:
  - `search_vacancies()` с фильтрами text/area/salary/schedule/experience/employment
  - `get_vacancy()` для полной карточки
  - `HHClientError` для ошибок API
- `app/services/vacancy.py` — pydantic-модели `Vacancy`, `Salary`:
  - `Vacancy.from_hh()` парсит сырой ответ HH
  - `Vacancy.short_text()` рендерит HTML для Telegram
- `app/api/vacancies.py` — FastAPI роутер `GET /vacancies` с фильтрами
- `app/main.py` — подключён роутер, добавлен startup-лог
- `app/bot/main.py` — Telegram-бот на polling:
  - `/start` — приветствие
  - `/jobs` — показ свежей невиденной вакансии
  - in-memory `viewed_ids` per chat
- `tests/test_vacancy.py` — 4 теста парсера (без сети)
- `tests/test_hh_client.py` — 2 теста клиента с моком httpx
- `pyproject.toml` — конфиг ruff + pytest-asyncio

### Initial setup
- README, LICENSE, .gitignore, .env.example, requirements.txt
- Project structure scaffolded (app/, tests/, docs/)
- Roadmap defined: Stage 1–4
