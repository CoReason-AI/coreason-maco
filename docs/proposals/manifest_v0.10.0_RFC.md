# RFC: Coreason Manifest v0.10.0 Recommendations

## Overview

Based on the integration experience with `coreason-maco` (Runtime Engine) and `coreason-manifest` v0.9.0, the following changes are recommended for v0.10.0 to improve developer experience (DX), type safety, and runtime flexibility.

## 1. Runtime Flexibility: Inline Agent Overrides

### Problem
In v0.9.0, `AgentNode` strictly references an agent via `agent_name`. It removed the generic `config` dict. While this enforces a clean separation between "Graph" and "Agent Definition", it makes ad-hoc experimentation difficult.
For example, to run the same "Writer" agent with different temperature settings in two different nodes, one must currently register two distinct agents ("WriterHot", "WriterCold") in the registry.

### Recommendation
Introduce an optional `runtime_config` or `overrides` field to `AgentNode`.

```python
class AgentNode(Node):
    type: Literal["agent"]
    agent_name: str

    # New Field
    overrides: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Runtime overrides for the agent (e.g., temperature, prompt_template_vars)."
    )
```

**Benefit:** Allows the graph to contextualize general-purpose agents without proliferation of agent definitions.

## 2. Type Safety: Generic Event Payloads

### Problem
`GraphEvent` currently defines `payload` as `Dict[str, Any]`.
```python
class GraphEvent(BaseModel):
    event_type: str
    payload: Dict[str, Any]
    ...
```
This forces consumers to manually cast or validate the payload based on `event_type`.

### Recommendation
Leverage Pydantic Generics to strictly tie `event_type` to a specific payload model.

```python
T = TypeVar("T", bound=BaseModel)

class GraphEvent(BaseModel, Generic[T]):
    event_type: str
    payload: T
```

Or use a Discriminated Union if the set of events is closed:

```python
GraphEvent = Annotated[Union[
    GraphEventNodeStart,
    GraphEventNodeDone,
    ...
], Field(discriminator='event_type')]
```

**Benefit:** Static analysis tools (mypy) and IDEs can infer the payload structure immediately after checking the event type.

## 3. Developer Experience: Flattened Imports

### Problem
Imports are currently deep and somewhat fragmented:
```python
from coreason_manifest.definitions.topology import AgentNode, GraphTopology
from coreason_manifest.recipes import RecipeManifest
from coreason_manifest.definitions.events import NodeStarted
```

### Recommendation
Re-export primary core types from the top-level `__init__.py`.

```python
# usage
from coreason_manifest import (
    RecipeManifest,
    AgentNode,
    GraphTopology,
    NodeStarted
)
```

**Benefit:** Reduces friction for new developers and simplifies import statements in consumer code.

## 4. Integrity: Kernel-Side Graph Validation

### Problem
Currently, `coreason-maco` implements `TopologyEngine.validate_graph` to check for cycles and disconnected islands. This logic is fundamental to the correctness of a `GraphTopology`.

### Recommendation
Move basic structural validation into `coreason-manifest`.
`GraphTopology` could have a method `.validate()` or a validator that ensures:
1.  All edge sources/targets exist in `nodes`.
2.  (Optional) The graph is acyclic (DAG).

**Benefit:** Centralizes integrity logic. Any consumer (UI, Engine, Linter) benefits from the same validation rules without re-implementing graph algorithms.

## 5. Metadata: Generalized Node Annotations

### Problem
`Node` has `visual: VisualMetadata`. This is specific to UI rendering.
However, engines often need other metadata, such as:
- Cost tracking tags ("cost_center": "marketing").
- Latency SLAs ("timeout_ms": 500).
- execution hints ("requires_gpu": true).

### Recommendation
Add a `metadata` field to `Node`.

```python
class Node(BaseModel):
    id: str
    visual: Optional[VisualMetadata]

    # New Field
    metadata: Dict[str, Any] = Field(default_factory=dict)
```

**Benefit:** Allows the manifest to carry operational context that the engine can use for scheduling, auditing, or resource allocation, beyond just UI layout.
