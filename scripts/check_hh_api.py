#!/usr/bin/env python3
"""Диагностика HH API: проверяет /me и /vacancies с текущим токеном.

Читает HH_ACCESS_TOKEN из .env и делает два GET-запроса:
  GET https://api.hh.ru/me
  GET https://api.hh.ru/vacancies?text=python&per_page=1

Выводит HTTP-статус по каждому запросу.
При ошибке — первые 500 символов ответа.
Токен в лог НЕ печатается.

Запуск:
    python scripts/check_hh_api.py
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import httpx
from dotenv import load_dotenv

load_dotenv(ROOT / ".env")

from app.core.config import settings

HH_BASE = "https://api.hh.ru"


def check(client: httpx.Client, label: str, url: str, params: dict | None = None) -> None:
    print(f"\n→ {label}")
    print(f"  URL: {url}" + (f"  params: {params}" if params else ""))
    try:
        response = client.get(url, params=params, timeout=10)
        print(f"  HTTP {response.status_code}", end="")
        if response.status_code == 200:
            data = response.json()
            # Для /me выводим email/id, для /vacancies — found
            if "found" in data:
                print(f"  — найдено вакансий: {data['found']}")
            elif "id" in data:
                print(f"  — id: {data['id']}, email: {data.get('email', 'н/д')}")
            else:
                print()
        else:
            print(f"\n  ⚠️  Ответ: {response.text[:500]}")
            if response.status_code == 403:
                print("  ❌ 403 Forbidden — проверьте HH_ACCESS_TOKEN в .env")
    except httpx.RequestError as e:
        print(f"  ❌ Ошибка сети: {e}")


def main() -> None:
    token = settings.hh_access_token

    headers: dict[str, str] = {
        "User-Agent": settings.hh_user_agent,
        "Accept": "application/json",
    }

    if token:
        headers["Authorization"] = f"Bearer {token}"
        masked = f"***{token[-6:]}" if len(token) > 6 else "***"
        print(f"🔑 HH_ACCESS_TOKEN задан (…{masked})")
    else:
        print("⚠️  HH_ACCESS_TOKEN не задан — запросы пойдут без авторизации (ожидается 403)")

    with httpx.Client(headers=headers) as client:
        check(client, "GET /me", f"{HH_BASE}/me")
        check(client, "GET /vacancies?text=python&per_page=1", f"{HH_BASE}/vacancies", {"text": "python", "per_page": 1})

    print("\nДиагностика завершена.")


if __name__ == "__main__":
    main()
