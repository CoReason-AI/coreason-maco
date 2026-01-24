from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI

from coreason_api.utils.logger import logger


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    # Startup
    logger.info("Starting up...")
    yield
    # Shutdown
    logger.info("Shutting down...")


app = FastAPI(
    title="CoReason API",
    description="The Central Nervous System of the CoReason Platform",
    version="0.1.0",
    lifespan=lifespan,
)


@app.get("/health")
async def health_check() -> dict[str, str]:
    return {"status": "ok", "version": "0.1.0"}
