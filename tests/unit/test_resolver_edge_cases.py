# Copyright (c) 2025 CoReason, Inc.
#
# This software is proprietary and dual-licensed.
# Licensed under the Prosperity Public License 3.0 (the "License").
# A copy of the license is available at https://prosperitylicense.com/versions/3.0.0
# For details, see the LICENSE file.
# Commercial use beyond a 30-day trial requires a separate license.
#
# Source Code: https://github.com/CoReason-AI/coreason_maco

from typing import Any

from coreason_maco.engine.resolver import VariableResolver


class MockObject:
    def __init__(self, **kwargs: Any) -> None:
        for k, v in kwargs.items():
            setattr(self, k, v)

    def my_method(self) -> str:
        return "called"


def test_resolve_none_in_path() -> None:
    """Test accessing a property on a None value in the chain."""
    resolver = VariableResolver()
    node_outputs = {"A": {"b": None}}
    # A.b is None. A.b.c should fail resolution.
    config = {"key": "{{ A.b.c }}"}
    resolved = resolver.resolve(config, node_outputs)
    assert resolved["key"] == "{{ A.b.c }}"


def test_resolve_double_dots() -> None:
    """Test double dots in path."""
    resolver = VariableResolver()
    node_outputs = {"A": {"b": "value"}}
    # A..b -> looks for attribute "" on A.
    config = {"key": "{{ A..b }}"}
    resolved = resolver.resolve(config, node_outputs)
    assert resolved["key"] == "{{ A..b }}"


def test_resolve_method_access() -> None:
    """Test accessing a method on an object."""
    resolver = VariableResolver()
    obj = MockObject()
    node_outputs = {"A": obj}
    config = {"key": "{{ A.my_method }}"}
    resolved = resolver.resolve(config, node_outputs)
    # Should resolve to string representation of the method
    assert "bound method" in str(resolved["key"]) or "method" in str(resolved["key"])


def test_resolve_numeric_string_key() -> None:
    """Test accessing a dictionary key that looks like a number."""
    resolver = VariableResolver()
    node_outputs = {"A": {"0": "zero", "1": "one"}}
    config = {"key": "{{ A.0 }}"}
    resolved = resolver.resolve(config, node_outputs)
    assert resolved["key"] == "zero"


def test_resolve_numeric_int_key_fails() -> None:
    """Test accessing a dictionary key that is an integer (should fail as we split to strings)."""
    resolver = VariableResolver()
    node_outputs = {"A": {0: "zero"}}  # Key is int 0
    config = {"key": "{{ A.0 }}"}
    resolved = resolver.resolve(config, node_outputs)
    # Fails because '0' (str) is not 0 (int)
    assert resolved["key"] == "{{ A.0 }}"


def test_resolve_deep_mixed_structure() -> None:
    """Test a deep structure with mixed lists, dicts, and objects."""
    # Lists are not traversable by dot notation in this implementation (no index support),
    # but traversing PAST a list is impossible.
    # We can only test Dict/Obj traversal.

    obj = MockObject(attr="success")
    # A -> dict -> dict -> obj -> attr
    resolver = VariableResolver()
    node_outputs = {"A": {"b": {"c": obj}}}
    config = {"key": "{{ A.b.c.attr }}"}
    resolved = resolver.resolve(config, node_outputs)
    assert resolved["key"] == "success"


def test_resolve_empty_key_in_dict() -> None:
    """Test if we can actually access an empty string key if it exists."""
    resolver = VariableResolver()
    node_outputs = {"A": {"": "hidden"}}
    # A. -> split yields ["A", ""]
    # Regex {{ A. }} might not match?
    # Regex is [\w\-_\.]+
    # Trailing dot is allowed by regex.
    config = {"key": "{{ A. }}"}
    resolved = resolver.resolve(config, node_outputs)
    assert resolved["key"] == "hidden"
