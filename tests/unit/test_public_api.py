# Copyright (c) 2025 CoReason, Inc.
#
# This software is proprietary and dual-licensed.
# Licensed under the Prosperity Public License 3.0 (the "License").
# A copy of the license is available at https://prosperitylicense.com/versions/3.0.0
# For details, see the LICENSE file.
# Commercial use beyond a 30-day trial requires a separate license.
#
# Source Code: https://github.com/CoReason-AI/coreason_maco

import pytest


def test_public_api_imports() -> None:
    """
    Verify that the main components are exposed at the top level package.
    """
    try:
        from coreason_maco import GraphEvent, WorkflowController, WorkflowRunner
    except ImportError as e:
        pytest.fail(f"Failed to import public API: {e}")

    assert WorkflowRunner is not None
    assert WorkflowController is not None
    assert GraphEvent is not None


def test_hello_world() -> None:
    from coreason_maco import hello_world

    assert hello_world() == "Hello World!"
