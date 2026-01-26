# Copyright (c) 2025 CoReason, Inc.
#
# This software is proprietary and dual-licensed.
# Licensed under the Prosperity Public License 3.0 (the "License").
# A copy of the license is available at https://prosperitylicense.com/versions/3.0.0
# For details, see the LICENSE file.
# Commercial use beyond a 30-day trial requires a separate license.
#
# Source Code: https://github.com/CoReason-AI/coreason_maco

from typing import Any, Dict

from coreason_maco.engine.resolver import PreserveUndefined, VariableResolver


class MockObject:
    def __init__(self, **kwargs: Any) -> None:
        for k, v in kwargs.items():
            setattr(self, k, v)


def test_resolve_simple_key() -> None:
    resolver = VariableResolver()
    node_outputs = {"A": "Hello"}
    config = {"key": "{{ A }}"}
    resolved = resolver.resolve(config, node_outputs)
    assert resolved["key"] == "Hello"


def test_resolve_nested_dict() -> None:
    resolver = VariableResolver()
    node_outputs = {"A": {"nested": "value"}}
    config = {"key": "{{ A.nested }}"}
    resolved = resolver.resolve(config, node_outputs)
    assert resolved["key"] == "value"


def test_resolve_nested_object() -> None:
    resolver = VariableResolver()
    obj = MockObject(attr="value")
    node_outputs = {"A": obj}
    config = {"key": "{{ A.attr }}"}
    resolved = resolver.resolve(config, node_outputs)
    assert resolved["key"] == "value"


def test_resolve_mixed_dict_object() -> None:
    resolver = VariableResolver()
    # A is dict, B inside is Object
    obj = MockObject(attr="success")
    node_outputs = {"A": {"B": obj}}
    config = {"key": "{{ A.B.attr }}"}
    resolved = resolver.resolve(config, node_outputs)
    assert resolved["key"] == "success"


def test_resolve_partial_match_is_string_replacement() -> None:
    resolver = VariableResolver()
    node_outputs = {"A": "World"}
    # Not exact match -> string replacement
    config = {"key": "Hello {{ A }}"}
    resolved = resolver.resolve(config, node_outputs)
    assert resolved["key"] == "Hello World"


def test_resolve_missing_key_keeps_template() -> None:
    # If part of the path is missing, it should NOT replace
    resolver = VariableResolver()
    node_outputs = {"A": {"nested": "value"}}
    config = {"key": "{{ A.missing }}"}
    resolved = resolver.resolve(config, node_outputs)
    # Jinja default behavior for undefined attr on defined object is undefined
    # Our PreserveUndefined logic captures the last missing part
    assert resolved["key"] == "{{ missing }}"


def test_resolve_missing_attr_keeps_template() -> None:
    # If attribute is missing on object, it should NOT replace
    resolver = VariableResolver()
    obj = MockObject(attr="value")
    node_outputs = {"A": obj}
    config = {"key": "{{ A.missing }}"}
    resolved = resolver.resolve(config, node_outputs)
    assert resolved["key"] == "{{ missing }}"


def test_resolve_missing_node_keeps_template() -> None:
    # If the root node is missing
    resolver = VariableResolver()
    node_outputs: Dict[str, Any] = {"A": "exist"}
    config = {"key": "{{ B.attr }}"}
    resolved = resolver.resolve(config, node_outputs)
    assert resolved["key"] == "{{ B.attr }}"


def test_resolve_chained_undefined() -> None:
    """Test accessing nested properties on an undefined variable."""
    resolver = VariableResolver()
    node_outputs: Dict[str, Any] = {}
    config = {"key": "{{ missing.child.grandchild }}"}
    resolved = resolver.resolve(config, node_outputs)
    assert resolved["key"] == "{{ missing.child.grandchild }}"


def test_resolve_dict_access_undefined() -> None:
    """Test accessing dict key on undefined variable."""
    resolver = VariableResolver()
    node_outputs: Dict[str, Any] = {}
    config = {"key": "{{ missing['key'] }}"}
    resolved = resolver.resolve(config, node_outputs)
    # PreserveUndefined reconstructs dict access as dot notation or whatever str(name) is
    # Our implementation: return PreserveUndefined(name=f"{self._undefined_name}.{name}")
    # So it becomes {{ missing.key }} usually, unless we implement __getitem__ specifically to format brackets.
    # Current implementation does f"{self._undefined_name}.{name}" which mimics dot notation.
    # Jinja parses ['key'] as item access.
    assert resolved["key"] == "{{ missing.key }}"


def test_preserve_undefined_direct() -> None:
    """Test PreserveUndefined class edge cases directly for coverage."""
    # Test __str__ with no name
    u = PreserveUndefined()
    assert str(u) == ""

    # Test __getattr__ with no name (should not prepend dot)
    u_attr = u.some_attr
    assert str(u_attr) == "{{ some_attr }}"

    # Test __getitem__ with no name
    u_item = u["some_item"]
    assert str(u_item) == "{{ some_item }}"
