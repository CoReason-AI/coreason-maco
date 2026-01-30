# Recipe Manifest Schema

The Coreason MACO engine relies on a strict Pydantic v2 data model called the **RecipeManifest**. This specification defines the structure, behavior, and visual representation of a "Recipe" — a deterministic Directed Acyclic Graph (DAG) that orchestrates strategic workflows.

The schema is defined in `src/coreason_maco/core/manifest_schema.py`.

## Overview

A **Recipe** is composed of:
1.  **Metadata**: Identifying information (`id`, `version`, `name`).
2.  **Inputs**: A schema defining the global variables required to execute the recipe.
3.  **Graph Topology**: A set of **Nodes** (steps) and **Edges** (connections).

## Root Model: `RecipeManifest`

The entry point for defining a workflow.

| Field | Type | Description |
| :--- | :--- | :--- |
| `id` | `str` | Unique identifier for the recipe. |
| `version` | `str` | Version of the recipe (e.g., "1.0.0"). |
| `name` | `str` | Human-readable name. |
| `description` | `str` | Optional detailed description. |
| `inputs` | `Dict[str, Any]` | Schema defining global variables this recipe accepts. |
| `graph` | `GraphTopology` | The topology definition containing `nodes` and `edges`. |

---

## Nodes (Polymorphic Steps)

Nodes represent individual steps in the workflow. The system uses a **Discriminated Union** based on the `type` field to support different behaviors.

### Common Attributes (All Nodes)

All nodes share these base attributes:

| Field | Type | Description |
| :--- | :--- | :--- |
| `id` | `str` | Unique identifier for the node. |
| `council_config` | `CouncilConfig` | Optional configuration for "Architectural Triangulation". |
| `visual` | `VisualMetadata` | UI-specific metadata (coordinates, icons, etc.). |

### Node Types

#### 1. AgentNode (`type="agent"`)
Invokes a specific atomic agent (e.g., a specialized LLM or tool).

-   **`agent_name`** (`str`): The name of the atomic agent to call.

#### 2. HumanNode (`type="human"`)
Pauses execution for user input or approval.

-   **`timeout_seconds`** (`Optional[int]`): Time in seconds before the step times out.

#### 3. LogicNode (`type="logic"`)
Executes pure Python logic for routing, formatting, or data transformation.

-   **`code`** (`str`): The Python logic to execute.

---

## Edges (Connections)

Edges define the flow of execution between nodes.

| Field | Type | Description |
| :--- | :--- | :--- |
| `source_node_id` | `str` | The ID of the source node. |
| `target_node_id` | `str` | The ID of the target node. |
| `condition` | `Optional[str]` | Python expression string (e.g., `"inputs.approval == True"`) for conditional branching. |

---

## Auxiliary Models

### CouncilConfig
Configuration for **Architectural Triangulation**, allowing multiple models/agents to vote or reach consensus.

-   **`strategy`** (`str`): The voting strategy (default: `"consensus"`).
-   **`voters`** (`List[str]`): List of agent IDs or model names participating in the council.

### VisualMetadata
Data explicitly for the "Living Canvas" UI.

-   **`label`** (`str`): Display label for the node.
-   **`x_y_coordinates`** (`List[float]`): `[x, y]` position on the canvas.
-   **`icon`** (`str`): Icon identifier.
-   **`animation_style`** (`str`): CSS animation style reference.

---

## Example JSON Representation

```json
{
  "id": "recipe-strategic-analysis",
  "version": "1.0.0",
  "name": "Strategic Market Analysis",
  "description": "Analyzes market trends and requires human approval before finalizing report.",
  "inputs": {
    "market_segment": "string",
    "depth": "integer"
  },
  "graph": {
    "nodes": [
      {
        "id": "node-research",
        "type": "agent",
        "agent_name": "market_researcher",
        "visual": {
          "label": "Gather Data",
          "x_y_coordinates": [100.0, 200.0],
          "icon": "search"
        }
      },
      {
        "id": "node-review",
        "type": "human",
        "timeout_seconds": 3600,
        "council_config": {
          "strategy": "consensus",
          "voters": ["gpt-4", "claude-3-opus"]
        },
        "visual": {
          "label": "Analyst Review",
          "x_y_coordinates": [300.0, 200.0]
        }
      },
      {
        "id": "node-finalize",
        "type": "logic",
        "code": "return {'status': 'published', 'data': inputs['research_data']}",
        "visual": {
          "label": "Publish Report",
          "x_y_coordinates": [500.0, 200.0]
        }
      }
    ],
    "edges": [
      {
        "source_node_id": "node-research",
        "target_node_id": "node-review"
      },
      {
        "source_node_id": "node-review",
        "target_node_id": "node-finalize",
        "condition": "result == 'APPROVED'"
      }
    ]
  }
}
```
