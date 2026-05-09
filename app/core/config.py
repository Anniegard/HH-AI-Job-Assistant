from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Telegram
    telegram_token: str = ""

    # HH API
    hh_base_url: str = "https://api.hh.ru"
    hh_client_id: str = ""
    hh_client_secret: str = ""
    hh_access_token: str = ""
    hh_user_agent: str = "HH-AI-Job-Assistant/0.1 (anniegard@github.com)"

    # OpenAI
    openai_api_key: str = ""
    # Overridable via USER_PROFILE in .env
    user_profile: str = (
        "Python/FastAPI automation developer with experience "
        "building production bots and data pipelines. "
        "Key projects: bot-mont-shk (Wildberries warehouse loss analytics "
        "automation -- tracks shortages, auto-generates claims, integrates "
        "with Google Sheets and Yandex Disk API); "
        "Habr Tech Radar Bot (Telegram bot that aggregates and ranks tech "
        "articles from Habr); "
        "anniland.ru (web platform with AI assistant demo). "
        "Stack: Python, FastAPI, aiogram/python-telegram-bot, "
        "Google Sheets API, Yandex Disk API, OpenAI API, PostgreSQL, Docker. "
        "Strong focus on AI automation workflows and Telegram/Web tooling. "
        "Looking for Python backend or automation roles involving bots, "
        "AI integration, or data pipelines."
    )

    # Resume context for cover letter generation
    # Overridable via RESUME_MD_PATH in .env
    resume_md_path: str = "profile/resume.md"

    # Google Sheets
    google_sheet_id: str = ""
    google_sheet_name: str = "CRM"
    google_credentials_path: str = "credentials.json"

    # Cover letter generation style.
    # "full"  -> 5-8 paragraphs, 1200-2200 chars (for relevant vacancies)
    # "short" -> 4-6 sentences (legacy behaviour)
    # Override via COVER_LETTER_STYLE in .env
    cover_letter_style: str = "full"
    # Max target character count for the generated letter.
    # Override via COVER_LETTER_MAX_CHARS in .env
    cover_letter_max_chars: int = 2200

    # App
    debug: bool = False
    log_level: str = "INFO"


settings = Settings()
