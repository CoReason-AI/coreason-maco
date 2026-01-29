# Copyright (c) 2025 CoReason, Inc.
#
# This software is proprietary and dual-licensed.
# Licensed under the Prosperity Public License 3.0 (the "License").
# A copy of the license is available at https://prosperitylicense.com/versions/3.0.0
# For details, see the LICENSE file.
# Commercial use beyond a 30-day trial requires a separate license.
#
# Source Code: https://github.com/CoReason-AI/coreason_maco

from typing import Any, Dict

from coreason_identity.models import UserContext

from coreason_maco.core.controller import WorkflowController
from coreason_maco.infrastructure.server_defaults import ServerRegistry
from coreason_maco.utils.logger import logger


def hello_world() -> str:
    logger.info("Hello World!")
    return "Hello World!"


async def run_workflow(manifest: Dict[str, Any], inputs: Dict[str, Any]) -> None:
    """CLI adapter to run a workflow."""
    services = ServerRegistry()
    controller = WorkflowController(services=services)

    system_context = UserContext(
        user_id="cli-user",
        email="cli@system.com",
        roles=["system"],
        metadata={"source": "cli"},
    )

    async for _ in controller.execute_recipe(manifest, inputs, context=system_context):
        # In a real CLI, we would print events
        pass
