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
    """Build the cover letter generation prompt (style v2).

    Extracted into a standalone function so it can be unit-tested
    independently of the OpenAI API call.
    """
    req_text = requirements or "не указаны"
    return (
        "Ты пишешь сопроводительное письмо для отклика на HH.ru от лица Дениса.\n"
        "Письмо должно быть персонализированным под вакансию, живым и конкретным.\n\n"
        "СТРОГИЕ ПРАВИЛА:\n"
        "1. Пиши ТОЛЬКО на русском языке.\n"
        "2. Используй ТОЛЬКО факты из профиля ниже — не выдумывай годы опыта, навыки, компании.\n"
        "3. Начни письмо со слова «Здравствуйте!».\n"
        "4. Не добавляй подпись (С уважением и т.п.).\n"
        "5. Не используй плейсхолдеры [Ваше имя], [название компании], [должность].\n"
        "6. Не используй длинное тире (—), только обычное (-).\n"
        "7. Не пиши «более 5 лет опыта» и не добавляй выдуманную статистику.\n"
        "8. Не пиши общих фраз без фактов: «мой опыт будет полезен вашей команде».\n\n"
        "СТРУКТУРА ПИСЬМА (5-8 коротких абзацев):\n"
        "1. «Здравствуйте!»\n"
        "2. Почему вакансия заинтересовала: 1 абзац с 1-2 конкретными сигналами из описания.\n"
        "3. Главный проект, наиболее релевантный вакансии: что делал, какой результат.\n"
        "4. Доп. AI-проекты, если вакансия про AI/LLM/автоматизацию (иначе пропусти).\n"
        "5. Стек - только то, что совпадает с вакансией.\n"
        "6. Рабочий подход: разобраться в процессе, найти узкие места, внедрить автоматизацию.\n"
        "7. Ссылки на GitHub (https://github.com/anniegard) и сайт (https://anniland.ru), если уместно.\n\n"
        "ДЛИНА:\n"
        "- Для релевантной вакансии: 1200-2200 символов.\n"
        "- Для слабо подходящей: 600-1000 символов.\n\n"
        f"Вакансия: {vacancy_title}\n"
        f"Компания: {company}\n"
        f"Требования/описание: {req_text}\n\n"
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
                temperature=0.7,
                max_tokens=800,
            )
            text = ((response.choices[0].message.content) or "").strip()
            if not text:
                raise OpenAIClientError("OpenAI returned an empty response")
            return text
        except OpenAIClientError:
            raise
        except Exception as e:
            raise OpenAIClientError(f"OpenAI API error: {e}") from e
