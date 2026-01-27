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

from jinja2 import Environment, TemplateSyntaxError, Undefined

from coreason_maco.utils.logger import logger


class PreserveUndefined(Undefined):  # type: ignore
    """Custom Undefined class that preserves the original variable name in the output.

    Example: {{ missing }} -> {{ missing }}
    """

    def __str__(self) -> str:
        # If accessing an attribute of an undefined variable, we reconstruct the path
        if self._undefined_name is None:
            return ""
        return f"{{{{ {self._undefined_name} }}}}"

    def __getattr__(self, name: str) -> Any:
        # Support chained access on undefined variables: {{ A.missing.child }}
        if self._undefined_name:
            new_name = f"{self._undefined_name}.{name}"
            return PreserveUndefined(name=new_name)
        return PreserveUndefined(name=name)

    def __getitem__(self, name: Any) -> Any:
        # Support dict access on undefined: {{ A['missing'] }}
        if self._undefined_name:
            new_name = f"{self._undefined_name}.{name}"
            return PreserveUndefined(name=new_name)
        return PreserveUndefined(name=str(name))


class VariableResolver:
    """Handles resolution of variables {{ node_id }} in configuration dictionaries using Jinja2."""

    def __init__(self) -> None:
        """Initializes the VariableResolver with a custom Jinja2 environment."""
        self.env = Environment(undefined=PreserveUndefined)

    def resolve(self, config: Dict[str, Any], node_outputs: Dict[str, Any]) -> Dict[str, Any]:
        """Recursively replaces {{ node_id }} with actual output values.

        Args:
            config: The configuration dictionary containing variables.
            node_outputs: Dictionary mapping node IDs to their outputs.

        Returns:
            Dict[str, Any]: The resolved configuration dictionary.
        """
        return self._replace_value(config, node_outputs)  # type: ignore

    def evaluate_boolean(self, expression: str, context: Dict[str, Any]) -> bool:
        """Evaluates a Jinja2 expression returning a boolean.

        Expects the rendered string to be "True", "False", "1", "0", etc.

        Args:
            expression: The boolean expression to evaluate.
            context: The context dictionary for variable substitution.

        Returns:
            bool: The result of the boolean evaluation.
        """
        try:
            # Check if expression is wrapped in brackets, if not, maybe it's just a value
            # But usually expressions for conditions should be {{ ... }}

            template = self.env.from_string(expression)
            rendered = template.render(**context)
            cleaned = rendered.strip().lower()
            return cleaned in ("true", "1", "yes", "on")
        except (TemplateSyntaxError, Exception) as e:
            # In case of syntax error or other issues, return False (fail safe)
            logger.warning(f"Jinja2 evaluation error: {e}. Expression: {expression}")
            return False

    def _replace_value(self, val: Any, context: Dict[str, Any]) -> Any:
        if isinstance(val, str):
            if "{{" in val and "}}" in val:
                try:
                    # Preservation Logic for Exact Matches:
                    # If the user asks for exactly "{{ node_id }}", we want to return the raw object (dict/list/etc)
                    # instead of the stringified version Jinja produces.
                    cleaned = val.strip()
                    if cleaned.startswith("{{") and cleaned.endswith("}}"):
                        inner = cleaned[2:-2].strip()

                        # Direct key access
                        if inner in context:
                            return context[inner]

                        # Dotted access support for object preservation
                        if "." in inner:
                            parts = inner.split(".")
                            current = context
                            found = True
                            for i, part in enumerate(parts):
                                if i == 0 and part in context:
                                    current = context[part]
                                    continue

                                if isinstance(current, dict) and part in current:
                                    current = current[part]
                                elif hasattr(current, part):
                                    current = getattr(current, part)
                                else:
                                    found = False
                                    break

                            if found:
                                return current

                    # Standard Jinja Render
                    template = self.env.from_string(val)
                    rendered = template.render(**context)

                    return rendered
                except (TemplateSyntaxError, Exception):
                    return val
            return val
        elif isinstance(val, dict):
            return {k: self._replace_value(v, context) for k, v in val.items()}
        elif isinstance(val, list):
            return [self._replace_value(v, context) for v in val]
        return val
