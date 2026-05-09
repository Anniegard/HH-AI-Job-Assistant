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
    """Build the cover letter generation prompt (style v3, живой HH-отклик).

    Extracted into a standalone function so it can be unit-tested
    independently of the OpenAI API call.
    """
    req_text = requirements or "не указаны"
    return (
        "Ты пишешь сопроводительное письмо для отклика на HH.ru от лица Дениса.\n"
        "Это ЖИВОЙ HH-отклик, а не email и не мотивационное письмо.\n"
        "Письмо должно быть персонализированным под вакансию, конкретным,\n"
        "уверенным, но не раздутым.\n\n"
        "СТРОГИЕ ПРАВИЛА:\n"
        "1. Пиши ТОЛЬКО на русском языке.\n"
        "2. Используй ТОЛЬКО факты из профиля ниже - не выдумывай годы опыта,\n"
        "   навыки, компании, проекты, цифры.\n"
        "3. Начни письмо со слова \"Здравствуйте!\".\n"
        "4. НЕ добавляй подпись \"С уважением\" и любую другую подпись.\n"
        "5. НЕ используй плейсхолдеры [Ваше имя], [название компании], [должность].\n"
        "6. НЕ используй длинное тире (—) и среднее тире (–) - только обычный\n"
        "   дефис (-) или запятую/точку.\n"
        "7. НЕ пиши \"более 5 лет опыта\" и не добавляй выдуманную статистику.\n"
        "8. ИЗБЕГАЙ общих фраз и канцелярита, в частности:\n"
        "   - \"ваша вакансия привлекла моё внимание благодаря...\"\n"
        "   - \"мой опыт будет полезен вашей команде\"\n"
        "   - \"значимый вклад\", \"огромный потенциал\", \"синергия\"\n"
        "   - \"являюсь специалистом, который...\"\n"
        "9. Тон уверенный, но НЕ раздутый: говори по делу о реальных проектах\n"
        "   и реальных навыках, без хвалебных эпитетов в свой адрес.\n\n"
        "СТРУКТУРА ПИСЬМА (5-7 коротких абзацев):\n"
        "1. \"Здравствуйте!\"\n"
        "2. 1 абзац: чем именно зацепила вакансия - 1-2 конкретных сигнала из\n"
        "   её описания (AI-автоматизации, боты, интеграции, контент, MVP и т.п.),\n"
        "   и почему это совпадает с тем, чем занимается Денис.\n"
        "3. Главный релевантный проект - описать конкретно: что делал, какой стек,\n"
        "   какой результат / какую ручную работу автоматизировал.\n"
        "4. (Опционально) Дополнительные AI/automation-кейсы, если вакансия про\n"
        "   AI / LLM / агентов / ботов / контент-автоматизацию.\n"
        "5. Стек: перечислить только то, что реально совпадает с вакансией.\n"
        "6. Рабочий подход: находить ручные процессы, быстро собирать прототип,\n"
        "   проверять пользу, описывать решение так, чтобы поняли команда,\n"
        "   пользователи или заказчик.\n"
        "7. Финальная строка: \"Буду рад обсудить...\", и ссылки на GitHub и сайт.\n"
        "   GitHub: https://github.com/Anniegard\n"
        "   Портфолио: https://anniland.ru/\n\n"
        "ВЫБОР ГЛАВНОГО ПРОЕКТА (важно):\n"
        "- Для AI automation / AI agents / bots / content automation / процессов /\n"
        "  внутренних инструментов / интеграций / Google Sheets / API / аналитики /\n"
        "  бизнес-процессов - ГЛАВНЫЙ кейс это bot-mont-shk\n"
        "  (Telegram/Web-бот для аналитики складских потерь Wildberries: Python,\n"
        "  FastAPI, Telegram bot, Google Sheets API, Yandex Disk API, Ubuntu VM;\n"
        "  экономит ~150 часов ручной работы в месяц).\n"
        "- ВТОРЫМ проектом для AI-вакансий упомяни AI-assistant_for_table_sellers\n"
        "  (демо AI-ассистента: подбор модели стола по росту, бюджету и сценарию;\n"
        "  пример AI-продукта с пользовательским сценарием и базой знаний).\n"
        "- Дополнительно коротко: HH AI Job Assistant и Habr Tech Radar Bot -\n"
        "  если вакансия про поиск, scoring, контент, аналитику, AI-инструменты.\n"
        "- НЕ делай AI-assistant_for_table_sellers главным кейсом автоматически\n"
        "  для любой AI-вакансии: чаще bot-mont-shk сильнее, потому что это\n"
        "  реальная бизнес-автоматизация с измеримым ROI.\n\n"
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
