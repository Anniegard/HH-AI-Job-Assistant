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

### Stage 4 — Polish & Deploy `[ планируется ]`
> Цель: стабильная production-like система

- [ ] Webhook вместо polling
- [ ] Деплой на сервер (Railway / VPS)
- [ ] Планировщик: авторассылка новых вакансий утром
- [ ] Обработка ошибок и edge cases
- [ ] Документация API

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

## 🔑 Переменные окружения

| Переменная | Описание |
|---|---|
| `TELEGRAM_TOKEN` | Bot token от @BotFather |
| `HH_CLIENT_ID` | Client ID приложения HH |
| `HH_CLIENT_SECRET` | Client Secret HH |
| `HH_ACCESS_TOKEN` | **Обязателен** — токен приложения для поиска вакансий |
| `OPENAI_API_KEY` | OpenAI API ключ |
| `GOOGLE_SHEET_ID` | ID Google Sheets таблицы |
| `GOOGLE_CREDENTIALS_PATH` | Путь к credentials.json |

---

## 📊 Google Sheets CRM

| Поле | Описание |
|---|---|
| Date | Дата добавления |
| Vacancy | Название вакансии |
| Company | Компания |
| URL | Ссылка на HH |
| Score | Оценка 0–100 |
| Status | new / viewed / saved / applied / interview / rejected / offer |
| Match Reason | Почему подходит |
| Cover Letter | Сгенерированное письмо |
| Response | Ответ работодателя |

---

## 🤖 Команды бота

| Команда | Описание |
|---|---|
| `/start` | Приветствие и помощь |
| `/jobs` | Показать новые вакансии |
| `/next` | Следующая вакансия |
| `/save` | Сохранить текущую |
| `/hide` | Скрыть / не интересно |
| `/coverletter` | Сгенерировать сопроводительное |

---

## 📝 Лицензия

MIT — см. [LICENSE](LICENSE)

---

> Проект создан как personal productivity tool и portfolio case по AI automation.
