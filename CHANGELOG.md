# Changelog

All notable changes to this project will be documented in this file.

---

## [unreleased] — 2026-05-09

### HH_ACCESS_TOKEN — стабильная авторизация для поиска вакансий

- `app/services/hh_client.py` — обновлён docstring (токен обязателен); конструктор корректно обрабатывает пустую строку (`"" → нет токена`); при 403 логируется понятная ошибка с подсказкой про `HH_ACCESS_TOKEN` (сам токен в лог не попадает)
- `.env.example` — `HH_ACCESS_TOKEN` стал явной переменной с комментарием о получении через `client_credentials`
- `scripts/get_hh_app_token.py` — новый скрипт: получает токен приложения через POST `/token` и печатает строку для вставки в `.env`
- `scripts/check_hh_api.py` — новый скрипт: диагностика `GET /me` и `GET /vacancies` с выводом HTTP-статусов
- `README.md` — добавлен блок «HH API access token» с пошаговой инструкцией; явно указано что OAuth redirect для поиска не нужен
- `tests/test_hh_client.py` — 3 новых теста: Authorization присутствует при наличии токена; отсутствует без токена; 403 содержит подсказку про `HH_ACCESS_TOKEN`

---

## [unreleased] — 2026-05-08

### Polish after Stage 3

- `app/bot/main.py` — все пользовательские сообщения переведены на русский (кнопки, статусы, ошибки, заголовок письма)
- `app/core/config.py` — `user_profile` заменён на реальный профиль Дениса (bot-mont-shk, Habr Tech Radar Bot, anniland.ru, полный стек)
- `app/services/openai_client.py` — восстановлены type hints; промпт усилен явным требованием русского языка и акцентом на релевантный опыт
- `app/services/sheets_client.py` — восстановлены type hints (`list[Any]`, `set[str]`)
- `app/services/crm_mapper.py` — восстановлены type hints (`list[str]` для `reasons` и возвращаемого значения)

---

## [unreleased] — 2026-05-08

### Stage 3 — AI Layer

- `app/services/openai_client.py` — исправлен API-вызов: `responses.create` → `chat.completions.create` (совместимость с openai 1.x); `max_output_tokens` → `max_tokens`
- `app/core/config.py` — добавлена настройка `user_profile` (переопределяется через `USER_PROFILE` в `.env`)
- `app/services/sheets_client.py` — новый метод `update_cover_letter(vacancy_url, text)` для сохранения письма в колонку H
- `app/services/crm_mapper.py` — добавлена колонка `cover_letter` (8-я, заполняется после генерации)
- `app/bot/main.py`:
  - `_generate_coverletter()` теперь читает профиль из `settings.user_profile`
  - выделена `_send_coverletter()` — единая точка отправки и сохранения в Sheets
  - `cmd_coverletter` и `on_button(coverletter)` используют общую функцию
- `.env.example` — добавлена переменная `USER_PROFILE`
- `tests/test_bot_callbacks.py` — обновлены тесты под реальную логику (убран плейсхолдер Stage 3); добавлены тесты на успешную генерацию через инлайн-кнопку
- `tests/test_bot_state.py` — добавлены тесты `cmd_coverletter`: успех + нет текущей вакансии
- `tests/test_openai_client.py` — новый файл, 6 тестов: корректный ответ, trim, пустой ключ, пустой ответ, исключение SDK, состав промпта
- `tests/test_sheets_client.py` — добавлены тесты `update_cover_letter`: успех + URL не найден

---

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
