# Copyright (c) 2025 CoReason, Inc.
#
# This software is proprietary and dual-licensed.
# Licensed under the Prosperity Public License 3.0 (the "License").
# A copy of the license is available at https://prosperitylicense.com/versions/3.0.0
# For details, see the LICENSE file.
# Commercial use beyond a 30-day trial requires a separate license.
#
# Source Code: https://github.com/CoReason-AI/coreason_maco

import re
from typing import Any, Dict


class VariableResolver:
    """
    Handles resolution of variables {{ node_id }} in configuration dictionaries.
    """

    def resolve(self, config: Dict[str, Any], node_outputs: Dict[str, Any]) -> Dict[str, Any]:
        """
        Recursively replaces {{ node_id }} with actual output values.
        """
        resolved = config.copy()
        return self._replace_value(resolved, node_outputs)  # type: ignore

    def _replace_value(self, val: Any, node_outputs: Dict[str, Any]) -> Any:
        if isinstance(val, str):
            # Regex to find {{ some_node_id }}
            # Allows alphanumeric, underscores, and hyphens
            matches = re.findall(r"\{\{\s*([\w\-_]+)\s*\}\}", val)
            for node_ref in matches:
                if node_ref in node_outputs:
                    # If the string is EXACTLY the template, replace with the raw object (e.g. dict/int)
                    if val.strip() == f"{{{{ {node_ref} }}}}":
                        return node_outputs[node_ref]
                    # Otherwise replace string content
                    val = val.replace(f"{{{{ {node_ref} }}}}", str(node_outputs[node_ref]))
            return val
        elif isinstance(val, dict):
            return {k: self._replace_value(v, node_outputs) for k, v in val.items()}
        elif isinstance(val, list):
            return [self._replace_value(v, node_outputs) for v in val]
        return val
