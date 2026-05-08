from __future__ import annotations

from openai import OpenAI

from app.core.config import settings


class OpenAIClientError(RuntimeError):
    pass


class OpenAIClient:
    def __init__(self, api_key=None, model="gpt-4o-mini"):
        self._api_key = api_key or settings.openai_api_key
        self._model = model

    def generate_cover_letter(self, *, vacancy_title, company, requirements="", user_profile=""):
        if not self._api_key:
            raise OpenAIClientError("OPENAI_API_KEY not set. Add key to .env")

        client = OpenAI(api_key=self._api_key)

        prompt = (
            "Generate a short cover letter for a job application on HH.ru. "
            "Style: confident, polite, no AI cliches, no filler. "
            "Length: 4-6 sentences, Russian language.\n\n"
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
