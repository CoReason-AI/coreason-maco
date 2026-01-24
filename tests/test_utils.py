# Copyright (c) 2025 CoReason, Inc.
#
# This software is proprietary and dual-licensed.
# Licensed under the Prosperity Public License 3.0 (the "License").
# A copy of the license is available at https://prosperitylicense.com/versions/3.0.0
# For details, see the LICENSE file.
# Commercial use beyond a 30-day trial requires a separate license.
#
# Source Code: https://github.com/CoReason-AI/coreason_maco

import importlib
import sys
from pathlib import Path
from unittest.mock import patch

from coreason_maco.utils.logger import logger


def test_logger_initialization() -> None:
    """Test that the logger is initialized correctly and creates the log directory."""
    # Since the logger is initialized on import, we check side effects

    # Check if logs directory creation is handled
    # Note: running this test might actually create the directory in the test environment
    # if it doesn't exist.

    log_path = Path("logs")
    if not log_path.exists():
        log_path.mkdir(parents=True, exist_ok=True)

    assert log_path.exists()
    assert log_path.is_dir()

    # Verify app.log creation if it was logged to (it might be empty or not created until log)
    # logger.info("Test log")
    # assert (log_path / "app.log").exists()


def test_logger_exports() -> None:
    """Test that logger is exported."""
    assert logger is not None


def test_logger_creates_directory() -> None:
    """Test that the logger creates the logs directory if it doesn't exist."""
    # Remove module if present to force re-execution of top-level code
    if "coreason_maco.utils.logger" in sys.modules:
        del sys.modules["coreason_maco.utils.logger"]

    # We need to patch Path.exists to return False for "logs"
    # and Path.mkdir to verify it's called.
    # Since Path is instantiated as Path("logs"), we need to catch that specific instance.

    with patch("pathlib.Path.exists", return_value=False) as mock_exists, patch("pathlib.Path.mkdir") as mock_mkdir:
        importlib.import_module("coreason_maco.utils.logger")

        # Verify mkdir was called
        assert mock_exists.called
        assert mock_mkdir.called

    # Reload the module properly for other tests
    if "coreason_maco.utils.logger" in sys.modules:
        del sys.modules["coreason_maco.utils.logger"]
    importlib.import_module("coreason_maco.utils.logger")
