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

### Stage 1 — Foundation `[ в разработке ]`
> Цель: рабочий скелет, можно запустить локально

- [ ] Структура проекта и окружение
- [ ] HH API клиент (поиск вакансий, фильтры)
- [ ] FastAPI backend — базовый эндпоинт `/vacancies`
- [ ] Базовый Telegram-бот (команды `/start`, `/jobs`)
- [ ] `.env` конфиг, логирование

---

### Stage 2 — Core Features `[ следующий ]`
> Цель: MVP, которым можно пользоваться каждый день

- [ ] Scoring Engine — оценка вакансий 0–100 по профилю
- [ ] Команды `/next`, `/save`, `/hide`
- [ ] Inline-кнопки: 👍 👎 📌 ✉
- [ ] Google Sheets интеграция (CRM: статусы, история)
- [ ] Дедупликация: не показывать уже просмотренные вакансии

---

### Stage 3 — AI Layer `[ планируется ]`
> Цель: AI-генерация сопроводительных писем

- [ ] OpenAI интеграция
- [ ] Промпт под профиль (портфолио, стек, стиль)
- [ ] Команда `/coverletter`
- [ ] Короткий HH-style отклик без AI-клише

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
# Заполни .env своими ключами

# 4. Запуск
uvicorn app.main:app --reload
```

---

## 🔑 Переменные окружения

| Переменная | Описание |
|---|---|
| `TELEGRAM_TOKEN` | Bot token от @BotFather |
| `HH_CLIENT_ID` | Client ID приложения HH |
| `HH_CLIENT_SECRET` | Client Secret HH |
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
