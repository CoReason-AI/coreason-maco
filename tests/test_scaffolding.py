import shutil
from importlib.metadata import version
from pathlib import Path

import networkx
import pydantic

import coreason_maco.core
import coreason_maco.engine
import coreason_maco.events
import coreason_maco.strategies
from coreason_maco.main import hello_world

# We need to reload logger to trigger the top-level code if we want to cover 'mkdir'
# but top-level code runs on import.
# Since it's already imported, we might not hit it unless we force reload or mock before import?
# But it's already imported by pytest collection.
# However, we can test the logic by extracting it or just ensuring 'logs' dir doesn't exist before import?
# Too late.


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
    # This is tricky because logger.py runs on import.
    # But we can verify the side effect (logs dir created).
    assert Path("logs").exists()

    # To cover the 'if not exists: mkdir', we would need to run this logic when dir doesn't exist.
    # Since we can't easily unload the module, we can import it in a subprocess or use reload.
    # But for now, let's see if the environment already has logs dir.
    # If we delete it and reload...

    import importlib

    import coreason_maco.utils.logger

    # Remove logs dir if exists
    if Path("logs").exists():
        shutil.rmtree("logs")

    # Reload
    importlib.reload(coreason_maco.utils.logger)

    assert Path("logs").exists()
