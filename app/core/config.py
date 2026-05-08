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
    # HH требует осмысленный User-Agent: https://github.com/hhru/api/blob/master/docs/general.md#user-agent
    # ВАЖНО: example.com и т.п. в чёрном списке. Замени на реальный email/url.
    # Формат: <AppName>/<Version> (<contact>)
    hh_user_agent: str = "HH-AI-Job-Assistant/0.1 (anniegard@github.com)"

    # OpenAI
    openai_api_key: str = ""

    # Google Sheets
    google_sheet_id: str = ""
    google_sheet_name: str = "CRM"
    google_credentials_path: str = "credentials.json"

    # App
    debug: bool = False
    log_level: str = "INFO"


settings = Settings()
