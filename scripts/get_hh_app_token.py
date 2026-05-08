#!/usr/bin/env python3
"""Получение токена приложения HH через client_credentials.

Читает HH_CLIENT_ID и HH_CLIENT_SECRET из .env,
отправляет POST на https://api.hh.ru/token,
печатает access_token, token_type и expires_in.

Токен НЕ сохраняется в .env автоматически — вставьте его вручную:
    HH_ACCESS_TOKEN=<полученный токен>

Запуск:
    python scripts/get_hh_app_token.py
"""

from __future__ import annotations

import sys
from pathlib import Path

# Добавляем корень проекта в sys.path, чтобы импортировать app
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import httpx
from dotenv import load_dotenv

load_dotenv(ROOT / ".env")

from app.core.config import settings

HH_TOKEN_URL = "https://api.hh.ru/token"


def main() -> None:
    client_id = settings.hh_client_id
    client_secret = settings.hh_client_secret

    if not client_id or not client_secret:
        print(
            "❌ HH_CLIENT_ID и/или HH_CLIENT_SECRET не заданы в .env.\n"
            "   Зарегистрируйте приложение на https://dev.hh.ru/admin и заполните .env."
        )
        sys.exit(1)

    print(f"Запрашиваем токен для приложения (client_id=***{client_id[-4:]}) ...")

    try:
        response = httpx.post(
            HH_TOKEN_URL,
            data={
                "grant_type": "client_credentials",
                "client_id": client_id,
                "client_secret": client_secret,
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            timeout=15,
        )
    except httpx.RequestError as e:
        print(f"❌ Ошибка сети: {e}")
        sys.exit(1)

    if response.status_code != 200:
        print(f"❌ HTTP {response.status_code}")
        print(f"   Ответ: {response.text[:500]}")
        sys.exit(1)

    data = response.json()
    access_token = data.get("access_token", "")
    token_type = data.get("token_type", "")
    expires_in = data.get("expires_in", "")

    print("\n✅ Токен получен!")
    print(f"   token_type : {token_type}")
    print(f"   expires_in : {expires_in} сек (~{int(expires_in) // 3600} ч)" if expires_in else "   expires_in : н/д")
    print(f"\n   access_token:\n   {access_token}")
    print(
        "\n📋 Вставьте в .env:\n"
        f"   HH_ACCESS_TOKEN={access_token}"
    )
    print(
        "\n🔍 Проверьте токен:\n"
        "   python scripts/check_hh_api.py"
    )


if __name__ == "__main__":
    main()
