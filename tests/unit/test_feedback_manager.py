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

import pytest

from coreason_maco.utils.context import FeedbackManager


@pytest.mark.asyncio  # type: ignore
async def test_feedback_manager() -> None:
    fm = FeedbackManager()

    # Test create
    loop = asyncio.get_running_loop()
    f1 = fm.create("n1", loop)
    assert "n1" in fm
    assert fm["n1"] is f1
    assert fm.get("n1") is f1

    # Test create implicit loop
    _ = fm.create("n2")
    assert "n2" in fm

    # Test set_result
    fm.set_result("n1", "val")
    assert f1.done()
    assert f1.result() == "val"

    # Test set_result duplicate (should be ignored)
    fm.set_result("n1", "val2")
    assert f1.result() == "val"

    # Test setitem
    f3 = loop.create_future()
    fm["n3"] = f3
    assert fm.get("n3") is f3
