# Architecture

## Flow

```
User (Telegram)
     │
     ▼
Telegram Bot  (python-telegram-bot)
     │  commands: /jobs /next /save /hide /coverletter
     │  buttons:  👍 👎 📌 ✉
     ▼
FastAPI Backend
     │
     ├──► HH API Client  ──────────► hh.ru
     │         │
     │         ▼
     ├──► Scoring Engine  (rule-based, 0–100)
     │
     ├──► LLM Service  ────────────► OpenAI API
     │         │ generate cover letter
     │
     └──► Sheets Service  ─────────► Google Sheets (CRM)
```

## Modules

| Module | Path | Stage |
|---|---|---|
| FastAPI app | `app/main.py` | 1 |
| Config | `app/core/config.py` | 1 |
| HH API client | `app/services/hh_client.py` | 1 |
| Telegram bot | `app/bot/main.py` | 1 |
| Scoring engine | `app/scoring/engine.py` | 2 |
| Google Sheets | `app/services/sheets.py` | 2 |
| OpenAI / LLM | `app/services/llm.py` | 3 |

## Data Model (Google Sheets CRM)

```
Date | Vacancy | Company | URL | Score | Status | Match Reason | Cover Letter | Response
```

Statuses: `new → viewed → saved → applied → interview → rejected → offer`
