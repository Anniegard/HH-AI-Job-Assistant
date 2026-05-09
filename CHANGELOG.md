# Changelog

All notable changes to this project will be documented in this file.

---

## [unreleased] — 2026-05-09

### Scoring v2 + cover letter style v3 — fix(scoring): improve AI automation vacancy matching

- `app/scoring/engine.py` — полностью переписан `ScoringEngine`. Добавлена нормализация текста (lowercase, ё→е, strip HTML, длинные тире/дефисы → пробел, схлопывание пробелов). Скоринг 0-100 разбит на 5 категорий: A. Target role match (до 30, AI-автоматизации/нейросети/AI-агенты/боты), B. Technical implementation (до 30, Python/FastAPI/API/Telegram/Sheets/OpenAI/n8n/Make/no-code), C. Product/content packaging (до 20, MVP/гипотезы/инструкции/гайды/кейсы/контент/база знаний), D. Working conditions (до 10, удалёнка/гибрид/junior/middle/AI-направление), E. Penalties (до -35, Java/C++/1С/.NET/Ruby/iOS/Android/sales/devops/frontend/heavy ML без automation/senior без AI/офис-only). Поддерживаются и русские, и английские варианты. Reasons возвращаются на русском (`AI-автоматизации`, `боты/AI-ассистенты`, `Python/API/интеграции`, `no-code/low-code`, `контентная упаковка`, `продуктовые гипотезы` и т.п.) с дедупом
- `app/bot/main.py` — добавлен helper `_build_scoring_payload(vacancy)`: пытается получить полное описание через `HHClient.get_vacancy(id)`, очищает HTML и кладёт в `payload["description"]`; при `HHClientError` — тихий fallback на snippet. `_show_next` теперь скорит по полному payload, а не только по snippet. UI выводит до 4 reasons (`reasons[:4]`)
- `app/services/openai_client.py` — `build_coverletter_prompt` v3 «живой HH-отклик»: 5-7 коротких абзацев, без подписи, без плейсхолдеров, без длинных тире, без канцелярита («ваша вакансия привлекла моё внимание», «мой опыт будет полезен», «значимый вклад»). Добавлены явные инструкции по выбору главного кейса: для AI automation / AI agents / bots / content automation / API / Sheets / интеграций — главный это `bot-mont-shk` (а не `AI-assistant_for_table_sellers`); вторым идёт `AI-assistant_for_table_sellers`; дополнительно `HH AI Job Assistant`/`Habr Tech Radar Bot`. Ссылки `https://github.com/Anniegard` и `https://anniland.ru/`
- `profile/resume.md` — `bot-mont-shk` помечен как главный коммерческий кейс (бизнес-автоматизация с измеримым ROI ~150 ч/мес), `AI-assistant_for_table_sellers` явно как демо AI sales assistant. Раздел «Персонализация по типу вакансии» обновлён: для AI automation / AI builder / AI content automation / process / API / Sheets — главный кейс `bot-mont-shk`, не `AI-assistant_for_table_sellers`
- `tests/test_scoring.py` — переписан под новый движок: `test_webmasters_like_vacancy_scores_high` (>=80 + reasons `AI-автоматизации`, `боты/AI-ассистенты`, `контентная упаковка`), `test_russian_ai_keywords_score_high`, `test_python_automation_vacancy_scores_well`, `test_1c_accountant_does_not_score_high`, `test_java_backend_does_not_score_high`, `test_pure_frontend_role_does_not_score_high`, `test_score_is_clamped_to_0_100`, `test_reasons_are_unique_and_in_russian`, `test_handles_html_tags_in_description`, `test_handles_yo_letter`, `test_office_only_penalty_applied`, плюс юнит-тесты на `normalize_text`
- `tests/test_openai_client.py` — добавлены `test_prompt_describes_live_hh_response_style`, `test_prompt_picks_bot_mont_shk_for_automation_vacancies`, `test_prompt_warns_against_making_table_assistant_primary`, `test_prompt_forbids_long_dash`, `test_prompt_forbids_generic_phrases`, `test_prompt_includes_github_and_anniland_links`

WebMasters «Специалист по AI-автоматизациям» теперь даёт 90/100 (было 20/100). Все 57 тестов проходят, `python -m compileall app` и `ruff check` чистые.

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
