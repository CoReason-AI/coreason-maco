# Copyright (c) 2025 CoReason, Inc.
#
# This software is proprietary and dual-licensed.
# Licensed under the Prosperity Public License 3.0 (the "License").
# A copy of the license is available at https://prosperitylicense.com/versions/3.0.0
# For details, see the LICENSE file.
# Commercial use beyond a 30-day trial requires a separate license.
#
# Source Code: https://github.com/CoReason-AI/coreason_maco

from typing import Any, Protocol


class ToolRegistry(Protocol):
    """
    Interface for the tool registry (coreason-mcp).
    """

    async def execute_tool(self, tool_name: str, args: dict[str, Any]) -> Any:
        """Executes a tool."""
        ...


class ServiceRegistry(Protocol):
    """
    Dependency Injection container.
    """

    @property
    def tool_registry(self) -> ToolRegistry:
        """Returns the tool registry service."""
        ...

    @property
    def auth_manager(self) -> Any:
        """Returns the auth manager service."""
        ...

    @property
    def audit_logger(self) -> Any:
        """Returns the audit logger service."""
        ...
