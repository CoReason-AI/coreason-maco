# Coreason Manifest Kernel Integration Guide

## Overview

`coreason-maco` (Runtime Engine) relies on `coreason-manifest` (Shared Kernel) for defining the data structures of workflows, agents, and events.
Starting from `coreason-maco` v0.5.0, the engine strictly adheres to `coreason-manifest` v0.9.0+.

## Key Concepts & Structures

### 1. RecipeManifest
The root definition of a workflow.
*   **Source:** `coreason_manifest.recipes.RecipeManifest`
*   **Key Fields:**
    *   `id`, `version`, `name`
    *   `topology`: Contains `nodes` and `edges`.
    *   `interface`: Inputs/Outputs schema.
    *   `state`: Global state schema.
    *   `parameters`: Global parameters.

### 2. GraphTopology
The graph structure.
*   **Source:** `coreason_manifest.definitions.topology.GraphTopology`
*   **Key Fields:**
    *   `nodes`: List of polymorphic nodes (`AgentNode`, `HumanNode`, `LogicNode`, etc.).
    *   `edges`: List of `Edge`.

### 3. AgentNode
Represents a step in the workflow executed by an agent.
*   **Source:** `coreason_manifest.definitions.topology.AgentNode`
*   **Key Fields:**
    *   `type`: "agent"
    *   `agent_name`: The name of the agent to invoke.
    *   `council_config`: Optional `CouncilConfig` for voting strategies.
    *   **Note:** `AgentNode` does NOT contain the prompt or model configuration. It references an agent definition by name.

### 4. LogicNode (Tool)
Represents a deterministic logic step or tool execution.
*   **Source:** `coreason_manifest.definitions.topology.LogicNode`
*   **Key Fields:**
    *   `type`: "logic"
    *   `code`: Used by `coreason-maco` as the `tool_name`.

### 5. CouncilConfig
Configuration for Council of Models (Voting).
*   **Source:** `coreason_manifest.definitions.topology.CouncilConfig`
*   **Key Fields:**
    *   `strategy`: Voting strategy (e.g., "consensus", "majority").
    *   `voters`: List of agent names participating in the vote.

### 6. Events
Strictly typed events emitted during execution.
*   **Source:** `coreason_manifest.definitions.events.*`
*   **Types:** `NodeStarted`, `NodeCompleted`, `CouncilVote`, `GraphEvent`, etc.

## Migration to v0.9.0

If you are migrating from an older version of `coreason-maco`:

1.  **Topology Structure:** Nodes and edges are now nested under `topology`.
    *   Old: `{"nodes": [...], "edges": [...]}`
    *   New: `{"topology": {"nodes": [...], "edges": [...]}}`

2.  **Node Configuration:**
    *   Inline `config` in `AgentNode` is no longer supported. Use `agent_name` to reference an agent.
    *   Prompt and model details should be managed via the Agent Registry or provided via `AgentExecutor`.

3.  **Council:**
    *   `CouncilNode` type is removed. Use `AgentNode` with `council_config`.
    *   `CouncilConfig` now expects `voters` (list of names) and `strategy`, instead of `agents` (list of dicts).

## Runtime Behavior

*   **Logic Mapping:**
    *   `AgentNode` -> `LLMNodeHandler` (delegates to `CouncilNodeHandler` if `council_config` exists).
    *   `LogicNode` -> `ToolNodeHandler` (maps `code` to `tool_name`).
    *   `HumanNode` -> `HumanNodeHandler`.

*   **Config Extraction:**
    *   `TopologyEngine` extracts `agent_name` from `AgentNode` and passes it as `config`.
    *   `TopologyEngine` passes `council_config` object in `config["council_config"]` if present.
