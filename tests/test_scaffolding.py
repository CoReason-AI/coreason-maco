from importlib.metadata import version

import networkx
import pydantic

import coreason_maco.core
import coreason_maco.engine
import coreason_maco.events
import coreason_maco.strategies


def test_dependencies_installed() -> None:
    assert pydantic.__version__
    assert networkx.__version__
    assert version("anyio")


def test_modules_importable() -> None:
    assert coreason_maco.core is not None
    assert coreason_maco.engine is not None
    assert coreason_maco.events is not None
    assert coreason_maco.strategies is not None
