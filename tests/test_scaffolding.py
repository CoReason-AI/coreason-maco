import shutil
from importlib.metadata import version
from pathlib import Path

import networkx
import pydantic
from loguru import logger

import coreason_maco.core
import coreason_maco.engine
import coreason_maco.events
import coreason_maco.strategies
from coreason_maco.main import hello_world


def test_dependencies_installed() -> None:
    assert pydantic.__version__
    assert networkx.__version__
    assert version("anyio")


def test_modules_importable() -> None:
    assert coreason_maco.core is not None
    assert coreason_maco.engine is not None
    assert coreason_maco.events is not None
    assert coreason_maco.strategies is not None


def test_hello_world() -> None:
    assert hello_world() == "Hello World!"


def test_logger_setup() -> None:
    """
    Test that the logger setup creates the logs directory.
    """
    # Verify the side effect (logs dir created)
    assert Path("logs").exists()

    # To cover the 'if not exists: mkdir', we force a reload.
    # CRITICAL: We MUST remove existing handlers to close the file handle
    # before attempting to delete the directory, otherwise Windows throws PermissionError.
    logger.remove()

    import importlib

    import coreason_maco.utils.logger

    # Remove logs dir if exists
    if Path("logs").exists():
        shutil.rmtree("logs")

    # Reload the module to trigger the top-level execution again
    importlib.reload(coreason_maco.utils.logger)

    assert Path("logs").exists()
