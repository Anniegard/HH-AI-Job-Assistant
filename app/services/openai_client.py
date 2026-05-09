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
    score: int | None = None,
    strengths: list[str] | None = None,
    risks: list[str] | None = None,
) -> str:
    """Build the cover letter generation prompt adapted to the vacancy match score.

    score >= 80: confident, main case, 1200-1800 chars
    60 <= score < 80: normal, no "полностью соответствую", 1000-1500 chars
    40 <= score < 60: cautious/exploratory, 600-1000 chars
    score < 40: warning + short honest letter, no strong claims
    """
    req_text = requirements or "не указаны"
    score_val = score if score is not None else 70  # default: moderate confidence

    # --- Match level context ---
    if score_val >= 80:
        match_context = (
            f"УРОВЕНЬ МАТЧА: СИЛЬНЫЙ (score {score_val}/100).\n"
            "Пиши уверенное, конкретное письмо. Показывай главный релевантный кейс.\n"
            "Длина: 1200-1800 символов.\n"
        )
    elif score_val >= 60:
        match_context = (
            f"УРОВЕНЬ МАТЧА: ХОРОШИЙ (score {score_val}/100).\n"
            "Пиши конкретное письмо, но НЕ используй фразы типа "
            '"полностью соответствую", "идеально подхожу".\n'
            "Показывай релевантные кейсы, не натягивай.\n"
            "Длина: 1000-1500 символов.\n"
        )
    elif score_val >= 40:
        match_context = (
            f"УРОВЕНЬ МАТЧА: СРЕДНИЙ (score {score_val}/100).\n"
            "Пиши осторожное письмо в exploratory-стиле: "
            '"мне интересно попробовать это направление", '
            '"готов обсудить, как мой опыт может быть полезен".\n'
            "НЕ делай сильных заявлений о соответствии.\n"
            "Длина: 600-1000 символов.\n"
        )
    else:
        match_context = (
            f"УРОВЕНЬ МАТЧА: СЛАБЫЙ (score {score_val}/100).\n"
            "Пиши очень короткое, честное письмо без натяжек.\n"
            "Не претендуй на полное соответствие.\n"
            "Длина: 400-700 символов.\n"
        )

    # --- Strengths/risks context for the prompt ---
    strengths_text = ""
    if strengths:
        top = ", ".join(strengths[:5])
        strengths_text = f"Совпадения с вакансией: {top}.\n"

    risks_text = ""
    if risks:
        top = ", ".join(risks[:3])
        risks_text = (
            f"Риски / слабые места: {top}.\n"
            "НЕ натягивай эти области - лучше умолчать, чем выглядеть неловко.\n"
        )

    return (
        "Ты пишешь сопроводительное письмо для отклика на HH.ru от лица Дениса.\n"
        "Это ЖИВОЙ HH-отклик, а не email и не мотивационное письмо.\n"
        "Письмо должно быть персонализированным под вакансию, конкретным,\n"
        "уверенным (в меру match level), но не раздутым.\n\n"
        f"{match_context}"
        f"{strengths_text}"
        f"{risks_text}"
        "\n"
        "СТРОГИЕ ПРАВИЛА:\n"
        "1. Пиши ТОЛЬКО на русском языке.\n"
        "2. Используй ТОЛЬКО факты из профиля ниже - не выдумывай годы опыта,\n"
        "   навыки, компании, проекты, цифры.\n"
        '3. Начни письмо со слова "Здравствуйте!".\n'
        '4. НЕ добавляй подпись "С уважением" и любую другую подпись.\n'
        "5. НЕ используй плейсхолдеры [Ваше имя], [название компании], [должность].\n"
        "6. НЕ используй длинное тире (--) и среднее тире (-) - только дефис (-)\n"
        "   или запятую/точку.\n"
        '7. НЕ пиши "более 5 лет опыта" и не добавляй выдуманную статистику.\n'
        "8. ИЗБЕГАЙ общих фраз:\n"
        '   - "ваша вакансия привлекла моё внимание благодаря..."\n'
        '   - "мой опыт будет полезен вашей команде"\n'
        '   - "значимый вклад", "огромный потенциал", "синергия"\n'
        '   - "являюсь специалистом, который..."\n'
        "9. Тон уверенный, но по делу: реальные проекты и навыки, без хвалебных\n"
        "   эпитетов в свой адрес.\n"
        "10. НЕ натягивай проекты под вакансию: если проект не совпадает с задачами\n"
        "    вакансии, не упоминай его как главный аргумент.\n\n"
        "СТРУКТУРА ПИСЬМА:\n"
        '1. "Здравствуйте!"\n'
        "2. 1 абзац: что зацепило в вакансии - 1-2 конкретных сигнала из описания.\n"
        "3. Главный релевантный проект - конкретно: что делал, стек, результат.\n"
        "4. (Опционально, если score >= 60) Дополнительный кейс.\n"
        "5. Стек: только то, что реально совпадает с вакансией.\n"
        "6. Рабочий подход: находить ручные процессы, быстро собирать прототип,\n"
        "   проверять пользу, описывать решение понятно для команды/заказчика.\n"
        '7. Финал: "Буду рад обсудить...", ссылки:\n'
        "   GitHub: https://github.com/Anniegard\n"
        "   Портфолио: https://anniland.ru/\n\n"
        "ВЫБОР ГЛАВНОГО ПРОЕКТА:\n"
        "- Для задач автоматизации / ботов / API / интеграций / Google Sheets /\n"
        "  внутренних инструментов / аналитики - ГЛАВНЫЙ кейс: bot-mont-shk\n"
        "  (Telegram/Web-бот для аналитики складских потерь Wildberries:\n"
        "  Python, FastAPI, Telegram bot, Google Sheets API, Yandex Disk API,\n"
        "  Ubuntu VM; экономит ~150 часов ручной работы в месяц).\n"
        "- bot-mont-shk ГЛАВНЫЙ только когда есть automation / process /\n"
        "  API / internal tools в задачах вакансии.\n"
        "- Для задач AI-ассистента / чат-бота / рекомендаций / диалогового продукта -\n"
        "  ГЛАВНЫЙ кейс: AI-assistant_for_table_sellers\n"
        "  (демо AI-ассистента: подбор стола по росту/бюджету/сценарию;\n"
        "  AI-продукт с пользовательским сценарием и базой знаний).\n"
        "- AI-assistant главный ТОЛЬКО когда роль реально про\n"
        "  AI-assistant / chatbot / conversation / product recommendation.\n"
        "- Дополнительно (если score >= 60): HH AI Job Assistant и\n"
        "  Habr Tech Radar Bot - для вакансий про поиск, scoring, контент,\n"
        "  аналитику, AI-инструменты.\n\n"
        f"Вакансия: {vacancy_title}\n"
        f"Компания: {company}\n"
        f"Требования/описание: {req_text}\n\n"
        f"Профиль кандидата:\n{resume_context}"
    )


def _weak_match_warning(score: int) -> str:
    """Prepend warning for low-score vacancies."""
    return (
        f"Вакансия слабый матч: {score}/100. "
        "Я бы не делал её приоритетной. "
        "Ниже осторожный вариант, если всё равно хотите откликнуться.\n\n"
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
        score: int | None = None,
        strengths: list[str] | None = None,
        risks: list[str] | None = None,
    ) -> str:
        if not self._api_key:
            raise OpenAIClientError("OPENAI_API_KEY not set. Add key to .env")

        client = OpenAI(api_key=self._api_key)

        prompt = build_coverletter_prompt(
            vacancy_title=vacancy_title,
            company=company,
            requirements=requirements,
            resume_context=user_profile or settings.user_profile,
            score=score,
            strengths=strengths,
            risks=risks,
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

            # Prepend warning for weak matches
            if score is not None and score < 40:
                text = _weak_match_warning(score) + text

            return text
        except OpenAIClientError:
            raise
        except Exception as e:
            raise OpenAIClientError(f"OpenAI API error: {e}") from e
