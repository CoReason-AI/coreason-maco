# src/coreason_maco/core/manifest.py

# Re-exporting from the Shared Kernel to maintain backward compatibility
# and provide a clean namespace for the engine.

from coreason_manifest.recipes import (
    RecipeManifest,
    GraphTopology,
    Node,
    AgentNode,
    HumanNode,
    LogicNode,
    Edge,
    CouncilConfig,
    VisualMetadata
)

__all__ = [
    "RecipeManifest",
    "GraphTopology",
    "Node",
    "AgentNode",
    "HumanNode",
    "LogicNode",
    "Edge",
    "CouncilConfig",
    "VisualMetadata"
]
