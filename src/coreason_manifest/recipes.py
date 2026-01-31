from typing import List, Literal, Optional, Dict, Any, Union, Annotated
from pydantic import BaseModel, ConfigDict, Field, StringConstraints

# 1. Versioning
# Strict Semantic Versioning Regex (Major.Minor.Patch)
VersionStr = Annotated[str, StringConstraints(pattern=r"^\d+\.\d+\.\d+$")]

# 2. Visual Metadata (The Living Canvas)
class VisualMetadata(BaseModel):
    model_config = ConfigDict(extra="forbid")

    x_y_coordinates: List[float]
    label: str
    icon: str

# 3. Governance (The Council)
class CouncilConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    strategy: str  # e.g., "consensus"
    voters: List[str]

# 4. Polymorphism - Node Types

# Base class is not strictly necessary for the union but helps with shared structure if needed.
# However, for Discriminated Union in Pydantic V2, separate models are clean.
# I will include 'id' and 'visual' and 'council' in all of them.
# To avoid repetition, I'll use a mixin or abstract base, but Pydantic models inherit fields.

class BaseNode(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str
    visual: VisualMetadata
    council: Optional[CouncilConfig] = None

class AgentNode(BaseNode):
    type: Literal["agent"]
    agent_name: str

class HumanNode(BaseNode):
    type: Literal["human"]
    timeout_seconds: int

class LogicNode(BaseNode):
    type: Literal["logic"]
    code: str

# Discriminated Union
Node = Annotated[
    Union[AgentNode, HumanNode, LogicNode],
    Field(discriminator="type")
]

# 5. Topology
class Edge(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source: str
    target: str
    condition: Optional[str] = None

class GraphTopology(BaseModel):
    model_config = ConfigDict(extra="forbid")

    nodes: List[Node]
    edges: List[Edge]

# 6. Root Object
class RecipeManifest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    version: VersionStr
    name: str
    description: str
    inputs: Dict[str, Any]
    graph: GraphTopology
