from __future__ import annotations

from openai import OpenAI

from app.core.config import settings


class OpenAIClientError(RuntimeError):
    """Ошибка генерации сопроводительного письма."""


class OpenAIClient:
    def __init__(self, api_key: str | None = None, model: str = "gpt-4o-mini") -> None:
        self._api_key = api_key or settings.openai_api_key
        self._model = model

    def generate_cover_letter(self, *, vacancy_title: str, company: str, requirements: str = "", user_profile: str = "") -> str:
        if not self._api_key:
            raise OpenAIClientError("OPENAI_API_KEY не задан. Добавь ключ в .env")

        client = OpenAI(api_key=self._api_key)

        prompt = (
            "Сгенерируй короткое сопроводительное письмо для отклика на HH.ru. "
            "Стиль: уверенный, вежливый, без AI-клише и воды. "
            "Длина: 4-6 предложений, русский язык.\n\n"
            f"Вакансия: {vacancy_title}\n"
            f"Компания: {company}\n"
            f"Требования: {requirements or 'не указаны'}\n"
            f"Профиль кандидата: {user_profile or 'Python разработчик, AI automation, FastAPI, Telegram bots'}"
        )

        try:
            response = client.responses.create(
                model=self._model,
                input=prompt,
                temperature=0.6,
                max_output_tokens=220,
            )
            text = (response.output_text or "").strip()
            if not text:
                raise OpenAIClientError("OpenAI вернул пустой ответ")
            return text
        except OpenAIClientError:
            raise
        except Exception as e:  # noqa: BLE001
            raise OpenAIClientError(f"Ошибка OpenAI API: {e}") from e
