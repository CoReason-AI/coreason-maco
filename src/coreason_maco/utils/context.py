# Copyright (c) 2025 CoReason, Inc.
#
# This software is proprietary and dual-licensed.
# Licensed under the Prosperity Public License 3.0 (the "License").
# A copy of the license is available at https://prosperitylicense.com/versions/3.0.0
# For details, see the LICENSE file.
# Commercial use beyond a 30-day trial requires a separate license.
#
# Source Code: https://github.com/CoReason-AI/coreason_maco

import asyncio
from contextvars import ContextVar
from typing import Any, Dict, Optional

from pydantic import BaseModel, ConfigDict, Field

try:
    from coreason_identity.models import UserContext
except ImportError:  # pragma: no cover
    UserContext = Any

# Context variable for tracing request IDs across async boundaries
request_id_var: ContextVar[str] = ContextVar("request_id", default="")


class FeedbackManager:
    """Manages futures for human-in-the-loop feedback.

    Wraps a dictionary to ensure reference passing in Pydantic.
    """

    def __init__(self) -> None:
        """Initializes the FeedbackManager."""
        self.futures: Dict[str, asyncio.Future[Any]] = {}

    def get(self, node_id: str) -> Optional[asyncio.Future[Any]]:
        """Gets the future for a specific node ID.

        Args:
            node_id: The ID of the node.

        Returns:
            Optional[asyncio.Future[Any]]: The future if it exists, else None.
        """
        return self.futures.get(node_id)

    def create(self, node_id: str, loop: asyncio.AbstractEventLoop | None = None) -> asyncio.Future[Any]:
        """Creates a new future for a node ID.

        Args:
            node_id: The ID of the node.
            loop: Optional event loop.

        Returns:
            asyncio.Future[Any]: The created future.
        """
        if loop is None:
            loop = asyncio.get_running_loop()
        f: asyncio.Future[Any] = loop.create_future()
        self.futures[node_id] = f
        return f

    def set_result(self, node_id: str, result: Any) -> None:
        """Sets the result for a node's future.

        Args:
            node_id: The ID of the node.
            result: The result to set.
        """
        if node_id in self.futures:
            if not self.futures[node_id].done():
                self.futures[node_id].set_result(result)

    def __contains__(self, item: str) -> bool:
        """Checks if a node ID exists in the manager."""
        return item in self.futures

    def __getitem__(self, item: str) -> asyncio.Future[Any]:
        """Gets the future for a node ID via indexing."""
        return self.futures[item]

    def __setitem__(self, key: str, value: asyncio.Future[Any]) -> None:
        """Sets the future for a node ID via indexing."""
        self.futures[key] = value


class ExecutionContext(BaseModel):
    """The Context Injection Object.

    Prevents MACO from needing direct access to Auth or DB drivers.

    Attributes:
        user_id: The ID of the user initiating the workflow.
        trace_id: The unique trace ID for the execution.
        secrets_map: Decrypted secrets passed from Vault.
        tool_registry: Interface for the tool registry (coreason-mcp).
        feedback_manager: Manager for human-in-the-loop feedback.
        user_context: The user identity passport (UserContext).
    """

    model_config = ConfigDict(extra="forbid", arbitrary_types_allowed=True)

    user_id: str
    trace_id: str
    secrets_map: Dict[str, str]  # Decrypted secrets passed from Vault
    tool_registry: Any  # Interface for coreason-mcp (The Tools)
    feedback_manager: FeedbackManager = Field(default_factory=FeedbackManager)
    user_context: Optional[UserContext] = None
