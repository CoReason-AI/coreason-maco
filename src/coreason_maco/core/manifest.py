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
    """Represents a single node in the workflow graph.

    Attributes:
        id: The unique identifier for the node.
        type: The type of the node (e.g., "LLM", "TOOL", "COUNCIL").
        config: Configuration parameters for the node.
    """

    model_config = ConfigDict(extra="forbid")

    id: str
    type: str  # e.g., "LLM", "TOOL", "COUNCIL"
    config: Dict[str, Any] = Field(default_factory=dict)


class EdgeModel(BaseModel):
    """Represents a directed edge between two nodes.

    Attributes:
        source: The ID of the source node.
        target: The ID of the target node.
        condition: Optional condition to activate the edge (e.g., "path_a").
    """

    model_config = ConfigDict(extra="forbid")

    source: str
    target: str
    condition: Optional[str] = None  # e.g., "path_a"


class RecipeManifest(BaseModel):
    """The Strategic Recipe definition.

    Attributes:
        name: The name of the recipe.
        version: The version of the recipe (default "1.0").
        nodes: List of nodes in the workflow.
        edges: List of edges in the workflow.
    """

    model_config = ConfigDict(extra="forbid")

    name: str
    version: str = "1.0"
    nodes: List[NodeModel]
    edges: List[EdgeModel]
