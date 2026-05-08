# HH API client — Stage 1
# Реализация в Stage 1: получение вакансий, фильтры

class HHClient:
    """Client for HeadHunter API."""

    BASE_URL = "https://api.hh.ru"

    def __init__(self, client_id: str, client_secret: str):
        self.client_id = client_id
        self.client_secret = client_secret

    async def search_vacancies(self, query: str, **filters) -> list[dict]:
        raise NotImplementedError("HH API client — Stage 1")
