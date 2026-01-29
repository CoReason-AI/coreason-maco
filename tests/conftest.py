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
from coreason_identity.models import UserContext

pytest_plugins = ("pytest_asyncio",)


@pytest.fixture  # type: ignore[untyped-decorator]
def anyio_backend() -> str:
    return "asyncio"


@pytest.fixture  # type: ignore[untyped-decorator]
def mock_user_context() -> UserContext:
    return UserContext(
        user_id="test-user",
        email="test@example.com",
        roles=["tester"],
        metadata={"source": "test"},
    )
