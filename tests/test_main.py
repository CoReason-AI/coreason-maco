# Copyright (c) 2025 CoReason, Inc.
#
# This software is proprietary and dual-licensed.
# Licensed under the Prosperity Public License 3.0 (the "License").
# A copy of the license is available at https://prosperitylicense.com/versions/3.0.0
# For details, see the LICENSE file.
# Commercial use beyond a 30-day trial requires a separate license.
#
# Source Code: https://github.com/CoReason-AI/coreason_maco

from typing import Any, AsyncGenerator
from unittest.mock import MagicMock

import pytest

from coreason_maco.events.protocol import GraphEvent
from coreason_maco.main import hello_world, run_workflow


def test_hello_world() -> None:
    assert hello_world() == "Hello World!"


@pytest.mark.asyncio  # type: ignore
async def test_run_workflow_cli() -> None:
    """Test the CLI adapter run_workflow function."""
    manifest = {"name": "Test", "nodes": [], "edges": []}
    inputs = {"trace_id": "test_cli"}

    # Mock WorkflowController
    with pytest.MonkeyPatch.context() as m:
        mock_controller = MagicMock()

        async def mock_execute(*args: Any, **kwargs: Any) -> AsyncGenerator[GraphEvent, None]:
            # Verify context is passed
            assert "context" in kwargs
            assert kwargs["context"].user_id == "cli-user"
            yield MagicMock(spec=GraphEvent)

        mock_controller.execute_recipe.side_effect = mock_execute

        # Mock class instantiation
        MockControllerCls = MagicMock(return_value=mock_controller)
        m.setattr("coreason_maco.main.WorkflowController", MockControllerCls)

        # Mock Registry
        MockRegistry = MagicMock()
        m.setattr("coreason_maco.main.ServerRegistry", MockRegistry)

        await run_workflow(manifest, inputs)

        MockControllerCls.assert_called_once()
