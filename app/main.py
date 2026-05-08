from fastapi import FastAPI

from app.api.vacancies import router as vacancies_router
from app.core.logging import logger

app = FastAPI(
    title="HH AI Job Assistant",
    description="Backend for Telegram bot that automates job search via HH API",
    version="0.1.0",
)

app.include_router(vacancies_router)


@app.on_event("startup")
async def on_startup() -> None:
    logger.info("HH AI Job Assistant starting up")


@app.get("/")
async def root() -> dict:
    return {"status": "ok", "service": "HH AI Job Assistant"}


@app.get("/health")
async def health() -> dict:
    return {"status": "healthy"}
