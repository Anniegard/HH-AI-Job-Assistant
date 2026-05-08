from __future__ import annotations

from openai import OpenAI

from app.core.config import settings


class OpenAIClientError(RuntimeError):
    pass


def build_coverletter_prompt(
    *,
    vacancy_title: str,
    company: str,
    requirements: str,
    resume_context: str,
) -> str:
    """Build the cover letter generation prompt.

    Extracted into a standalone function so it can be unit-tested
    independently of the OpenAI API call.
    """
    req_text = requirements or "не указаны"
    return (
        "Ты помогаешь кандидату написать отклик на вакансию для HH.ru.\n\n"
        "СТРОГИЕ ПРАВИЛА:\n"
        "1. Пиши ТОЛЬКО на русском языке.\n"
        "2. Используй ТОЛЬКО факты из профиля ниже — не выдумывай годы опыта, навыки, компании.\n"
        "3. Не добавляй приветствие (Уважаемые, Добрый день и т.п.).\n"
        "4. Не добавляй подпись (С уважением, Спасибо за внимание и т.п.).\n"
        "5. Не используй плейсхолдеры [Ваше имя], [название компании], [должность].\n"
        "6. Выбери 1-2 проекта из профиля, наиболее релевантных этой вакансии, и упомяни их конкретно.\n"
        "7. Пиши конкретно и по делу — без общих AI-клише.\n"
        "8. Длина ответа: ровно 4-6 предложений. Не больше.\n\n"
        f"Вакансия: {vacancy_title}\n"
        f"Компания: {company}\n"
        f"Требования: {req_text}\n\n"
        f"Профиль кандидата:\n{resume_context}"
    )


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

        prompt = build_coverletter_prompt(
            vacancy_title=vacancy_title,
            company=company,
            requirements=requirements,
            resume_context=user_profile or settings.user_profile,
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
