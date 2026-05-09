# HH AI Job Assistant 🤖

> Telegram-бот для автоматизации поиска работы через HeadHunter API с AI-генерацией сопроводительных писем.

![Python](https://img.shields.io/badge/Python-3.11+-blue?logo=python)
![FastAPI](https://img.shields.io/badge/FastAPI-0.110+-green?logo=fastapi)
![Telegram](https://img.shields.io/badge/Telegram-Bot-blue?logo=telegram)
![License](https://img.shields.io/badge/License-MIT-yellow)
![Status](https://img.shields.io/badge/Status-In%20Development-orange)

---

## 🎯 Что это

Личный AI-ассистент для поиска работы:
- получает свежие вакансии с HH.ru по нужным фильтрам
- автоматически скорирует каждую вакансию под твой профиль (0–100)
- генерирует короткое сопроводительное письмо в стиле HH без AI-клише
- логирует всё в Google Sheets как lightweight CRM

**Стек:** Python · FastAPI · python-telegram-bot · HH API · OpenAI API · Google Sheets API

---

## 🗺 Roadmap

### Stage 1 — Foundation `[ завершён ]`
> Цель: рабочий скелет, можно запустить локально

- [x] Структура проекта и окружение
- [x] HH API клиент (поиск вакансий, фильтры)
- [x] FastAPI backend — базовый эндпоинт `/vacancies`
- [x] Базовый Telegram-бот (команды `/start`, `/jobs`)
- [x] `.env` конфиг, логирование

---

### Stage 2 — Core Features `[ завершён ]`
> Цель: MVP, которым можно пользоваться каждый день

- [x] Scoring Engine — оценка вакансий 0–100 по профилю
- [x] Команды `/next`, `/save`, `/hide`
- [x] Inline-кнопки: 👍 👎 📌 ✉
- [x] Google Sheets интеграция (CRM: статусы, история)
- [x] Дедупликация: не показывать уже просмотренные вакансии

---

### Stage 3 — AI Layer `[ завершён ]`
> Цель: AI-генерация сопроводительных писем

- [x] OpenAI интеграция (`chat.completions`)
- [x] Профиль кандидата вынесен в конфиг (`USER_PROFILE` в `.env`)
- [x] Команда `/coverletter` + inline-кнопка `✉`
- [x] Короткий HH-style отклик без AI-клише (4–6 предложений, temp 0.6)
- [x] Сохранение письма в Google Sheets (колонка H `cover_letter`)

---

### Stage 3.5 — Google Sheets as persistent job CRM `[ завершён ]`
> Цель: Sheet как надёжная БД вакансий, без дублей и с сохранением статусов между сессиями

- [x] `vacancy_id` из HH как первичный ключ строки
- [x] `JobCRM` сервис (`app/services/job_crm.py`) поверх Google Sheets:
  - `load_jobs()`, `get_job_by_vacancy_id()`, `upsert_job()`
  - `update_status()`, `save_letter()`, `is_known()`, `should_skip()`
- [x] Приоритеты статусов: `new → viewed → letter_generated → saved → applied → interview`
- [x] Ручные финальные статусы `hidden` / `rejected` — не перезаписываются ботом
- [x] Письмо (`Letter`) и заметки (`notes`) не затираются пустым значением
- [x] Upsert по `vacancy_id`: нет дублей при повторном показе вакансии
- [x] Кнопки Telegram обновляют Sheet напрямую через CRM
- [x] Обратная совместимость: старые листы без новых колонок расширяются автоматически
- [x] Unit-тесты: `tests/test_job_crm.py` (29 тестов)

---

### Stage 4 — Daily AI Job Workflow `[ завершён ]`
> Цель: ежедневный AI-ассистент поиска работы — дайджест, профили, умный ранкинг

- [x] Команда `/daily` — топ-5 вакансий по активному профилю за день
- [x] 6 поисковых профилей: `ai_builder`, `python_automation`, `ai_automation`, `fastapi_backend`, `llm_engineer`, `ai_product_engineer`
- [x] Команды `/profiles` (список) и `/profile <name>` (смена профиля)
- [x] Calibration layer: compound-signal бусты (automation+API, Telegram bot, Google Sheets workflow, LLM platform) и штрафы (строгий опыт 5+, академический исследователь)
- [x] Компактный daily-формат карточки: #N, компания, оценка, плюсы/минусы, кнопки
- [x] Кнопка [Letter] в дейли-карточках — письмо для конкретной вакансии
- [x] Команда `/stats` — статистика CRM по статусам и профилям
- [x] Новые поля CRM: `last_seen_at`, `profile` (добавляются автоматически в существующий лист)
- [x] Unit-тесты Stage 4: `test_search_profiles.py`, `test_calibration.py`, `test_daily_workflow.py`

---

### 🚫 Не входит в MVP
`auto apply` · `web dashboard` · `multi-user` · `SaaS` · `browser extension` · `email parsing`

---

## 🏗 Архитектура

```
Telegram Bot
     ↓
FastAPI Backend
     ↓
HH API  →  Scoring Engine
                ↓
         LLM Cover Letter
                ↓
        Google Sheets CRM
```

---

## 📁 Структура проекта

```
HH-AI-Job-Assistant/
├── app/
│   ├── api/            # FastAPI роутеры
│   ├── bot/            # Telegram bot handlers
│   ├── services/       # HH API, Sheets, OpenAI клиенты
│   ├── scoring/        # Scoring engine
│   └── core/           # Конфиг, логирование
├── tests/
├── docs/
├── .env.example
├── requirements.txt
└── README.md
```

---

## ⚡ Быстрый старт

```bash
# 1. Клонировать
git clone https://github.com/Anniegard/HH-AI-Job-Assistant.git
cd HH-AI-Job-Assistant

# 2. Окружение
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt

# 3. Конфиг
cp .env.example .env
# Заполни .env своими ключами (см. блок ниже про HH_ACCESS_TOKEN)

# 4. Запуск
uvicorn app.main:app --reload
```

---

## 🔑 HH API access token

Для поиска вакансий (`/vacancies`) HH API **требует авторизацию** — без токена вернётся `403 Forbidden`.
Используется токен приложения, полученный через `client_credentials` (OAuth redirect при этом **не нужен**).

**Шаг 1.** Убедитесь, что в `.env` заполнены `HH_CLIENT_ID` и `HH_CLIENT_SECRET` (берутся из [dev.hh.ru/admin](https://dev.hh.ru/admin)).

**Шаг 2.** Получите токен приложения:

```bash
python scripts/get_hh_app_token.py
```

Скрипт выведет `access_token` — скопируйте его и вставьте в `.env`:

```
HH_ACCESS_TOKEN=IGPA3A...ваш_токен...
```

**Шаг 3.** Проверьте, что API работает:

```bash
python scripts/check_hh_api.py
```

Скрипт проверит `GET /me` и `GET /vacancies` и покажет HTTP-статусы. При `200` всё готово.

> **Примечание:** `HH_ACCESS_TOKEN` здесь — токен *приложения* (client credentials), а не пользователя.
> OAuth redirect через anniland.ru потребуется позже — для откликов от имени аккаунта пользователя.
> Для поиска вакансий он не нужен.

---

## 📄 Resume context

Сопроводительные письма генерируются на основе файла `profile/resume.md`.  
Он содержит целевые роли, стек, проекты и правила стиля — всё, что модель должна
использовать как единственный источник фактов.

**Как редактировать:** откройте `profile/resume.md` и обновите нужные разделы
(проекты, стек, целевые роли). Изменения применятся при следующем запросе `/coverletter`.

**Переопределить путь через `.env`:**

```
RESUME_MD_PATH=path/to/your_resume.md
```

Если файл не найден или пустой, бот автоматически использует `USER_PROFILE` из `.env`
как резервный контекст (fallback).

---

## 🔑 Переменные окружения

| Переменная | Описание |
|---|---|
| `TELEGRAM_TOKEN` | Bot token от @BotFather |
| `HH_CLIENT_ID` | Client ID приложения HH |
| `HH_CLIENT_SECRET` | Client Secret HH |
| `HH_ACCESS_TOKEN` | **Обязателен** — токен приложения для поиска вакансий |
| `OPENAI_API_KEY` | OpenAI API ключ |
| `RESUME_MD_PATH` | Путь к `profile/resume.md` (по умолчанию `profile/resume.md`) |
| `GOOGLE_SHEET_ID` | ID Google Sheets таблицы |
| `GOOGLE_CREDENTIALS_PATH` | Путь к credentials.json |

---

## 📊 Google Sheets CRM

| Поле | Описание |
|---|---|
| `date` | Дата добавления |
| `vacancy_id` | HH vacancy ID (первичный ключ) |
| `Name` | Название вакансии |
| `Company` | Компания |
| `Link` | Ссылка на HH |
| `Score` | Оценка 0–100 |
| `status` | new / viewed / letter_generated / saved / applied / interview / hidden / rejected |
| `Tags` | Причины совпадения (до 3) |
| `Letter` | Сгенерированное письмо |
| `notes` | Заметки пользователя |
| `updated_at` | Время последнего обновления |
| `last_seen_at` | Время последнего показа в /daily |
| `profile` | Профиль поиска, через который найдена вакансия |

Поля `last_seen_at` и `profile` добавляются автоматически в существующие листы при первом доступе.

---

## 🔍 Профили поиска (Stage 4)

| Профиль | Запрос |
|---|---|
| `ai_builder` | AI builder автоматизация Python LLM FastAPI Telegram |
| `python_automation` | Python автоматизация процессов API интеграция |
| `ai_automation` | AI автоматизация LLM no-code workflow |
| `fastapi_backend` | FastAPI Python backend REST API |
| `llm_engineer` | LLM engineer OpenAI GPT агент RAG |
| `ai_product_engineer` | AI product Python automation chatbot |

По умолчанию активен профиль `ai_builder`. Профиль хранится в памяти сессии (сбрасывается при перезапуске бота).

---

## 🤖 Команды бота

| Команда | Описание |
|---|---|
| `/start` | Приветствие и список команд |
| `/daily` | Топ-5 вакансий по активному профилю |
| `/jobs` | Показать следующую вакансию |
| `/next` | Пропустить текущую |
| `/save` | Сохранить текущую |
| `/hide` | Скрыть / не интересно |
| `/coverletter` | Сгенерировать сопроводительное письмо |
| `/profiles` | Список профилей поиска |
| `/profile <name>` | Сменить активный профиль |
| `/stats` | Статистика CRM |
| `/debug` | Вкл/выкл детальный разбор очков |

---

## 📝 Лицензия

MIT — см. [LICENSE](LICENSE)

---

> Проект создан как personal productivity tool и portfolio case по AI automation.
