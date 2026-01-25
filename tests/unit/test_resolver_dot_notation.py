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


def test_resolve_simple_node() -> None:
    resolver = VariableResolver()
    node_outputs = {"A": "value"}
    config = {"key": "{{ A }}"}
    resolved = resolver.resolve(config, node_outputs)
    assert resolved["key"] == "value"


def test_resolve_dict_dot_notation() -> None:
    resolver = VariableResolver()
    node_outputs = {"A": {"nested": "value"}}
    config = {"key": "{{ A.nested }}"}
    resolved = resolver.resolve(config, node_outputs)
    assert resolved["key"] == "value"


def test_resolve_object_dot_notation() -> None:
    resolver = VariableResolver()
    obj = MockObject(attr="value")
    node_outputs = {"A": obj}
    config = {"key": "{{ A.attr }}"}
    resolved = resolver.resolve(config, node_outputs)
    assert resolved["key"] == "value"


def test_resolve_nested_dot_notation() -> None:
    resolver = VariableResolver()
    node_outputs = {"A": {"level1": {"level2": "value"}}}
    config = {"key": "{{ A.level1.level2 }}"}
    resolved = resolver.resolve(config, node_outputs)
    assert resolved["key"] == "value"


def test_resolve_mixed_access() -> None:
    # Dict containing Object
    resolver = VariableResolver()
    obj = MockObject(final="value")
    node_outputs = {"A": {"middle": obj}}
    config = {"key": "{{ A.middle.final }}"}
    resolved = resolver.resolve(config, node_outputs)
    assert resolved["key"] == "value"


def test_resolve_missing_key_keeps_template() -> None:
    # If part of the path is missing, it should NOT replace
    resolver = VariableResolver()
    node_outputs = {"A": {"nested": "value"}}
    config = {"key": "{{ A.missing }}"}
    resolved = resolver.resolve(config, node_outputs)
    assert resolved["key"] == "{{ A.missing }}"


def test_resolve_missing_attr_keeps_template() -> None:
    # If attribute is missing on object, it should NOT replace
    resolver = VariableResolver()
    obj = MockObject(attr="value")
    node_outputs = {"A": obj}
    config = {"key": "{{ A.missing }}"}
    resolved = resolver.resolve(config, node_outputs)
    assert resolved["key"] == "{{ A.missing }}"


def test_resolve_missing_node_keeps_template() -> None:
    resolver = VariableResolver()
    node_outputs = {"A": "val"}
    config = {"key": "{{ B.nested }}"}
    resolved = resolver.resolve(config, node_outputs)
    assert resolved["key"] == "{{ B.nested }}"


def test_resolve_partial_string() -> None:
    resolver = VariableResolver()
    node_outputs = {"A": {"key": "World"}}
    config = {"key": "Hello {{ A.key }}!"}
    resolved = resolver.resolve(config, node_outputs)
    assert resolved["key"] == "Hello World!"


def test_resolve_list() -> None:
    resolver = VariableResolver()
    node_outputs = {"A": {"key": "value"}}
    config = {"key": ["{{ A.key }}"]}
    resolved = resolver.resolve(config, node_outputs)
    assert resolved["key"][0] == "value"


def test_resolve_other_types() -> None:
    resolver = VariableResolver()
    node_outputs: dict[str, Any] = {}
    config = {"key": 123, "none": None}
    resolved = resolver.resolve(config, node_outputs)
    assert resolved["key"] == 123
    assert resolved["none"] is None
