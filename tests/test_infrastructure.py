import importlib
import tomllib
from pathlib import Path

import networkx as nx
import pytest
from pydantic import BaseModel

import coreason_maco


def test_version_consistency() -> None:
    """Verify that the package version matches pyproject.toml."""
    pyproject_path = Path("pyproject.toml")
    with open(pyproject_path, "rb") as f:
        data = tomllib.load(f)

    toml_version = data["tool"]["poetry"]["version"]
    assert coreason_maco.__version__ == toml_version


def test_namespace_integrity() -> None:
    """Verify that the namespace is clean and does not allow random imports."""
    with pytest.raises(ImportError):
        importlib.import_module("coreason_maco.non_existent_module")


def test_package_structure() -> None:
    """Verify that the package structure matches the expected submodules."""
    expected_modules = ["core", "engine", "events", "strategies"]
    package_path = Path(coreason_maco.__path__[0])

    for module in expected_modules:
        # Check directory existence
        assert (package_path / module).is_dir()
        assert (package_path / module / "__init__.py").exists()

        # Check importability
        module_name = f"coreason_maco.{module}"
        imported_module = importlib.import_module(module_name)
        assert imported_module is not None


def test_dependency_functionality() -> None:
    """Verify that critical dependencies are functional."""
    # NetworkX
    G = nx.DiGraph()
    G.add_edge(1, 2)
    assert list(G.edges) == [(1, 2)]

    # Pydantic
    class TestModel(BaseModel):
        id: int
        name: str

    m = TestModel(id=1, name="test")
    assert m.id == 1
    assert m.name == "test"
