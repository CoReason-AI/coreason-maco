import logging
from typing import Any, Generator

import pytest
from fastapi.testclient import TestClient
from loguru import logger

from coreason_api.main import app


# Propagate loguru logs to standard logging for caplog compatibility
class PropagateHandler(logging.Handler):
    def emit(self, record: logging.LogRecord) -> None:
        logging.getLogger(record.name).handle(record)


@pytest.fixture(autouse=True)
def setup_logging() -> Generator[None, Any, None]:
    # Bridge loguru to standard logging for testing
    handler_id = logger.add(PropagateHandler(), format="{message}")
    yield
    logger.remove(handler_id)


def test_health_check_valid() -> None:
    """Test standard happy path for health check."""
    with TestClient(app) as client:
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json() == {"status": "ok", "version": "0.1.0"}


def test_health_check_invalid_method() -> None:
    """Edge Case: Test invalid HTTP method on health endpoint."""
    with TestClient(app) as client:
        response = client.post("/health")
        assert response.status_code == 405  # Method Not Allowed


def test_lifespan_logging(caplog: pytest.LogCaptureFixture) -> None:
    """Complex: Verify logging occurs during lifespan events."""
    with TestClient(app):
        # Startup happens on enter
        pass

    # Check if logs were captured
    # Note: loguru propagation might put messages in root or specific logger
    assert any("Starting up..." in r.message for r in caplog.records)
    assert any("Shutting down..." in r.message for r in caplog.records)
