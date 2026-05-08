from fastapi import FastAPI

app = FastAPI(
    title="HH AI Job Assistant",
    description="Backend for Telegram bot that automates job search via HH API",
    version="0.1.0",
)


@app.get("/")
async def root():
    return {"status": "ok", "service": "HH AI Job Assistant"}


@app.get("/health")
async def health():
    return {"status": "healthy"}
