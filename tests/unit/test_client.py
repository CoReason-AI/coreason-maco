from typing import Any, AsyncGenerator
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from coreason_maco.client import Service, ServiceAsync
from coreason_maco.events.protocol import GraphEvent


@pytest.mark.asyncio  # type: ignore[misc]
async def test_service_async_lifecycle_external_client() -> None:
    client_mock = AsyncMock()

    async with ServiceAsync(client=client_mock) as svc:
        assert svc._client == client_mock

    # Should not close external client
    client_mock.aclose.assert_not_called()


@pytest.mark.asyncio  # type: ignore[misc]
async def test_service_async_lifecycle_internal_client() -> None:
    with patch("httpx.AsyncClient") as mock_cls:
        mock_instance = AsyncMock()
        mock_cls.return_value = mock_instance

        async with ServiceAsync() as svc:
            assert svc._internal_client is True

        mock_instance.aclose.assert_awaited_once()


@pytest.mark.asyncio  # type: ignore[misc]
async def test_service_async_execute_recipe() -> None:
    service = ServiceAsync()

    e1 = MagicMock(spec=GraphEvent)
    e2 = MagicMock(spec=GraphEvent)

    # Create an async generator for the mock return value
    async def _async_gen(manifest: Any, inputs: Any, resume_snapshot: Any) -> AsyncGenerator[GraphEvent, None]:
        yield e1
        yield e2

    # Mock the controller
    service._controller = MagicMock()
    service._controller.execute_recipe.side_effect = _async_gen

    events = []
    async for event in service.execute_recipe({}, {}):
        events.append(event)

    assert events == [e1, e2]
    service._controller.execute_recipe.assert_called_once()


def test_service_sync_lifecycle() -> None:
    # Patch start_blocking_portal
    with patch("coreason_maco.client.start_blocking_portal") as mock_start_portal:
        mock_portal_cm = MagicMock()
        mock_start_portal.return_value = mock_portal_cm
        mock_portal = MagicMock()
        mock_portal_cm.__enter__.return_value = mock_portal

        # Patch ServiceAsync
        with patch("coreason_maco.client.ServiceAsync") as MockServiceAsync:
            mock_async_instance = AsyncMock()
            MockServiceAsync.return_value = mock_async_instance

            with Service():
                pass

            # Verify portal started
            mock_start_portal.assert_called_once()
            mock_portal_cm.__enter__.assert_called_once()

            # Verify async service initialized via portal
            mock_portal.call.assert_any_call(mock_async_instance.__aenter__)

            # Verify async service closed via portal (checking call count at least)
            assert mock_portal.call.call_count >= 2

            # Verify portal closed
            mock_portal_cm.__exit__.assert_called_once()


def test_service_sync_execute_recipe() -> None:
    e1 = MagicMock(spec=GraphEvent)
    e2 = MagicMock(spec=GraphEvent)

    # Patch start_blocking_portal
    with patch("coreason_maco.client.start_blocking_portal") as mock_start_portal:
        mock_portal = MagicMock()
        mock_start_portal.return_value.__enter__.return_value = mock_portal

        # We simulate return values for portal.call
        # 1. __aenter__ -> None
        # 2. execute_recipe -> [e1, e2]
        # 3. __aexit__ -> None
        mock_portal.call.side_effect = [None, [e1, e2], None]

        with patch("coreason_maco.client.ServiceAsync"):
            svc = Service()
            with svc:
                events = svc.execute_recipe({}, {})

            assert events == [e1, e2]
            # Ensure execute_recipe called portal.call
            assert mock_portal.call.call_count == 3


def test_service_sync_no_context() -> None:
    svc = Service()
    with pytest.raises(RuntimeError, match="Service must be used within a 'with' block"):
        svc.execute_recipe({}, {})


def test_service_sync_integration() -> None:
    """Test Service with real BlockingPortal but mocked ServiceAsync."""
    e1 = MagicMock(spec=GraphEvent)

    with patch("coreason_maco.client.ServiceAsync") as MockServiceAsync:
        mock_instance = MockServiceAsync.return_value

        # Mock execute_recipe to return async generator
        async def _mock_gen(*args: Any, **kwargs: Any) -> AsyncGenerator[GraphEvent, None]:
            yield e1

        mock_instance.execute_recipe.side_effect = _mock_gen
        mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
        mock_instance.__aexit__ = AsyncMock()

        svc = Service()
        with svc:
            # This runs with real portal!
            events = svc.execute_recipe({}, {})

        assert events == [e1]

        # Verify calls were propagated
        mock_instance.__aenter__.assert_called_once()
        mock_instance.__aexit__.assert_called_once()


def test_service_simple_coverage() -> None:
    """Ensure real Service + BlockingPortal runs end-to-end to catch __exit__ coverage."""
    # We patch httpx to avoid network calls, but let BlockingPortal run for real
    with patch("httpx.AsyncClient") as MockClient:
        # AsyncClient must return an async close method
        instance = MockClient.return_value
        instance.aclose = AsyncMock()

        with Service():
            pass
