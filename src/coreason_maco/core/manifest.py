# Copyright (c) 2025 CoReason, Inc.
#
# This software is proprietary and dual-licensed.
# Licensed under the Prosperity Public License 3.0 (the "License").
# A copy of the license is available at https://prosperitylicense.com/versions/3.0.0
# For details, see the LICENSE file.
# Commercial use beyond a 30-day trial requires a separate license.
#
# Source Code: https://github.com/CoReason-AI/coreason_maco

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field


class NodeModel(BaseModel):
    """
    Represents a single node in the workflow graph.
    """

    model_config = ConfigDict(extra="forbid")

    id: str
    type: str  # e.g., "LLM", "TOOL", "COUNCIL"
    config: Dict[str, Any] = Field(default_factory=dict)


class EdgeModel(BaseModel):
    """
    Represents a directed edge between two nodes.
    """

    model_config = ConfigDict(extra="forbid")

    source: str
    target: str
    condition: Optional[str] = None  # e.g., "path_a"


class RecipeManifest(BaseModel):
    """
    The Strategic Recipe definition.
    """

    model_config = ConfigDict(extra="forbid")

    name: str
    version: str = "1.0"
    nodes: List[NodeModel]
    edges: List[EdgeModel]
