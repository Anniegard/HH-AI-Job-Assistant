# Stage 1 — Foundation

**Цель:** рабочий скелет, можно запустить локально и получить вакансии через API.

---

## Checklist

- [ ] Структура проекта и виртуальное окружение
- [ ] `app/core/config.py` — загрузка переменных из `.env`
- [ ] `app/core/logging.py` — loguru логирование
- [ ] `app/services/hh_client.py` — HTTP клиент для HH API
  - [ ] `GET /vacancies` — поиск с фильтрами
  - [ ] Парсинг полей: id, name, employer, salary, url, description
  - [ ] Пагинация
- [ ] `app/api/vacancies.py` — FastAPI роутер `/vacancies`
- [ ] `app/bot/main.py` — базовый бот
  - [ ] `/start` — приветствие
  - [ ] `/jobs` — получить и показать 1 вакансию
- [ ] Тест вручную: запустить бота и получить вакансию

---

## Критерий выполнения

Бот отвечает на `/jobs` и показывает реальную вакансию с HH.ru.

---

## Ключевые решения

- Polling (не webhook) — проще для локальной разработки
- Храним `viewed_ids` в памяти — упрощает Stage 1, в Stage 2 переедем в Sheets
- Один запрос = одна вакансия, листаем по `/next`
