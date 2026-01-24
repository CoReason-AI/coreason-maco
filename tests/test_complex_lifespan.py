from contextlib import asynccontextmanager
from typing import AsyncGenerator

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient


def test_lifespan_startup_failure() -> None:
    """Complex: Test application behavior when startup fails."""

    @asynccontextmanager
    async def broken_lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
        raise RuntimeError("Startup failed")
        yield

    broken_app = FastAPI(lifespan=broken_lifespan)

    with pytest.raises(RuntimeError, match="Startup failed"):
        with TestClient(broken_app):
            pass
