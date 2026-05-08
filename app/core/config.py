from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    # Telegram
    telegram_token: str = ""

    # HH API
    hh_client_id: str = ""
    hh_client_secret: str = ""
    hh_access_token: str = ""

    # OpenAI
    openai_api_key: str = ""

    # Google Sheets
    google_sheet_id: str = ""
    google_credentials_path: str = "credentials.json"

    # App
    debug: bool = False
    log_level: str = "INFO"


settings = Settings()
