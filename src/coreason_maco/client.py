from types import TracebackType
from typing import Any, AsyncGenerator, Dict, List, Optional, Type

import httpx
from anyio.from_thread import BlockingPortal, start_blocking_portal
from coreason_identity.models import UserContext

from coreason_maco.core.controller import WorkflowController
from coreason_maco.core.interfaces import ServiceRegistry
from coreason_maco.events.protocol import GraphEvent
from coreason_maco.infrastructure.server_defaults import ServerRegistry


class ServiceAsync:
    """The Core: Async-native service implementation.

    Handles resource management and executes workflows asynchronously.
    """

    def __init__(
        self,
        client: Optional[httpx.AsyncClient] = None,
        service_registry: Optional[ServiceRegistry] = None,
    ) -> None:
        """Initializes the ServiceAsync.

        Args:
            client: Optional external httpx.AsyncClient.
            service_registry: Optional ServiceRegistry for dependency injection.
        """
        self._internal_client = client is None
        self._client = client or httpx.AsyncClient()
        self._services = service_registry or ServerRegistry()
        # Initialize controller
        self._controller = WorkflowController(services=self._services)

    async def __aenter__(self) -> "ServiceAsync":
        """Enters the async context."""
        return self

    async def __aexit__(
        self,
        exc_type: Optional[Type[BaseException]],
        exc_val: Optional[BaseException],
        exc_tb: Optional[TracebackType],
    ) -> None:
        """Exits the async context and cleans up resources."""
        if self._internal_client:
            await self._client.aclose()

    async def execute_recipe(
        self,
        manifest: Dict[str, Any],
        inputs: Dict[str, Any],
        *,
        context: UserContext,
        resume_snapshot: Dict[str, Any] | None = None,
    ) -> AsyncGenerator[GraphEvent, None]:
        """Executes a recipe asynchronously.

        Args:
            manifest: The recipe manifest.
            inputs: The input parameters.
            context: The user context.
            resume_snapshot: Optional snapshot to resume from.

        Yields:
            GraphEvent: Execution events.
        """
        async for event in self._controller.execute_recipe(
            manifest, inputs, context=context, resume_snapshot=resume_snapshot
        ):
            yield event


class Service:
    """The Facade: Synchronous wrapper for ServiceAsync.

    Provides a blocking interface for scripting and synchronous environments
    using a persistent event loop thread via anyio.BlockingPortal.
    """

    def __init__(
        self,
        client: Optional[httpx.AsyncClient] = None,
        service_registry: Optional[ServiceRegistry] = None,
    ) -> None:
        """Initializes the Service.

        Args:
            client: Optional external httpx.AsyncClient.
            service_registry: Optional ServiceRegistry.
        """
        self._async = ServiceAsync(client, service_registry)
        self._portal: Optional[BlockingPortal] = None
        self._portal_cm: Any = None

    def __enter__(self) -> "Service":
        """Enters the sync context, starting a background event loop."""
        self._portal_cm = start_blocking_portal()
        self._portal = self._portal_cm.__enter__()

        # Initialize async service inside the portal's loop
        self._portal.call(self._async.__aenter__)
        return self

    def __exit__(
        self,
        exc_type: Optional[Type[BaseException]],
        exc_val: Optional[BaseException],
        exc_tb: Optional[TracebackType],
    ) -> None:
        """Exits the sync context, cleaning up resources and the event loop."""
        try:
            if self._portal:
                self._portal.call(self._async.__aexit__, exc_type, exc_val, exc_tb)
        finally:
            if self._portal_cm:
                self._portal_cm.__exit__(exc_type, exc_val, exc_tb)
                self._portal_cm = None
                self._portal = None

    def execute_recipe(
        self,
        manifest: Dict[str, Any],
        inputs: Dict[str, Any],
        *,
        context: UserContext,
        resume_snapshot: Dict[str, Any] | None = None,
    ) -> List[GraphEvent]:
        """Executes a recipe synchronously and returns all events.

        Args:
            manifest: The recipe manifest.
            inputs: The input parameters.
            context: The user context.
            resume_snapshot: Optional snapshot to resume from.

        Returns:
            List[GraphEvent]: A list of all execution events.

        Raises:
            RuntimeError: If called outside of a context manager.
        """
        if not self._portal:
            raise RuntimeError("Service must be used within a 'with' block.")

        async def _run() -> List[GraphEvent]:
            events = []
            async for event in self._async.execute_recipe(
                manifest, inputs, context=context, resume_snapshot=resume_snapshot
            ):
                events.append(event)
            return events

        return self._portal.call(_run)  # type: ignore[no-any-return]
