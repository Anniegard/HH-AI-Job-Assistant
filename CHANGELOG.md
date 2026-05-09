# Changelog

All notable changes to this project will be documented in this file.

---

## [unreleased] — 2026-05-09

### Cover letter style v2

- `profile/resume.md` — новый раздел «Структура письма» (7 шагов) и «Персонализация по типу вакансии» (WB/e-commerce, AI/LLM, Python/API, no-code); формат изменён с «4-6 предложений» на «5-8 абзацев, 1200-2200 символов»; добавлено правило начинать с «Здравствуйте!»
- `app/services/openai_client.py` — промпт v2: убран запрет приветствия, добавлена структура из 7 пунктов (приветствие, почему вакансия, главный проект, AI-кейсы, стек, рабочий подход, ссылки); вставлены ссылки github.com/anniegard и anniland.ru; `max_tokens` 220→800, `temperature` 0.6→0.7
- `app/core/config.py` — добавлены настройки `cover_letter_style: str = "full"` и `cover_letter_max_chars: int = 2200` (переопределяются через `.env`)
- `app/bot/main.py` — `_generate_coverletter` стала async; добавлена `_strip_html()` для очистки HTML; загружает полное описание вакансии через `HHClient.get_vacancy()` с fallback на snippet при ошибке HH API
- `tests/test_openai_client.py` — тест `test_prompt_specifies_sentence_count` заменён на `test_prompt_specifies_format` (проверяет 1200/2200) и `test_prompt_starts_with_greeting_instruction`
- `tests/test_bot_callbacks.py` — добавлен `AsyncMock` для `HHClient.get_vacancy` чтобы избежать реальных сетевых вызовов в тестах

---

## [unreleased] — 2026-05-09

### Stage 3.5 — Resume Context

- `profile/resume.md` — новый файл с профилем кандидата: целевые роли, стек, AI-инструменты, проекты (bot-mont-shk, anniland.ru, AI-assistant_for_table_sellers, Habr Tech Radar Bot, HH AI Job Assistant) и правила стиля писем
- `app/core/resume.py` — новый модуль `load_resume_context(max_chars=6000)`: читает `resume.md` UTF-8, fallback на `settings.user_profile` при ошибке/пустом файле, логирует warning, не падает, обрезает до max_chars
- `app/core/config.py` — добавлена настройка `resume_md_path: str = "profile/resume.md"` (переопределяется через `RESUME_MD_PATH` в `.env`)
- `app/services/openai_client.py` — промпт вынесен в отдельную функцию `build_coverletter_prompt()` для тестируемости; промпт усилен: запрет выдумывать опыт/компании/навыки, запрет приветствий/подписей/плейсхолдеров, требование выбирать 1–2 релевантных проекта
- `app/bot/main.py` — `_generate_coverletter()` теперь использует `load_resume_context()` вместо `settings.user_profile`; fallback через `user_profile` сохранён
- `.env.example` — добавлена переменная `RESUME_MD_PATH`
- `README.md` — добавлен раздел «Resume context» с описанием файла, инструкцией по редактированию и переменной `RESUME_MD_PATH`
- `tests/test_resume_context.py` — 6 тестов: чтение файла, fallback при отсутствии файла, fallback при пустом файле, truncate max_chars, truncate fallback, нет исключений при OSError
- `tests/test_openai_client.py` — 6 новых тестов `build_coverletter_prompt`: наличие resume context, вакансии и компании, запрет выдумывать опыт, запрет подписей и плейсхолдеров, требование русского языка, ограничение 4–6 предложений

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
