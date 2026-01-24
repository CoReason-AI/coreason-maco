from fastapi import FastAPI

from core.logger import logger

app: FastAPI = FastAPI(title="CoReason API")


@app.get("/")  # type: ignore
async def root() -> dict[str, str]:
    logger.info("Health check endpoint called")
    return {"message": "CoReason API is running"}
