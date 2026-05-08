from __future__ import annotations

from openai import OpenAI

from app.core.config import settings


class OpenAIClientError(RuntimeError):
    pass


class OpenAIClient:
    def __init__(self, api_key: str | None = None, model: str = "gpt-4o-mini") -> None:
        self._api_key = api_key if api_key is not None else settings.openai_api_key
        self._model = model

    def generate_cover_letter(
        self,
        *,
        vacancy_title: str,
        company: str,
        requirements: str = "",
        user_profile: str = "",
    ) -> str:
        if not self._api_key:
            raise OpenAIClientError("OPENAI_API_KEY not set. Add key to .env")

        client = OpenAI(api_key=self._api_key)

        prompt = (
            "Write a short cover letter in Russian for a job application on HH.ru. "
            "IMPORTANT: the entire letter must be written in Russian. "
            "Style: confident, specific, polite -- no AI cliches, no filler phrases. "
            "Length: 4-6 sentences. Highlight relevant experience from the candidate "
            "profile that matches the vacancy requirements.\n\n"
            f"Vacancy: {vacancy_title}\n"
            f"Company: {company}\n"
            f"Requirements: {requirements or 'not specified'}\n"
            f"Candidate profile: {user_profile or 'Python developer, AI automation, FastAPI, Telegram bots'}"
        )

        try:
            response = client.chat.completions.create(
                model=self._model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.6,
                max_tokens=220,
            )
            text = ((response.choices[0].message.content) or "").strip()
            if not text:
                raise OpenAIClientError("OpenAI returned an empty response")
            return text
        except OpenAIClientError:
            raise
        except Exception as e:
            raise OpenAIClientError(f"OpenAI API error: {e}") from e
