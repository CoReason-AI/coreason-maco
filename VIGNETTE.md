# The Architecture and Utility of coreason-maco

## 1. The Philosophy (The Why)

In the current landscape of Generative AI, we face a critical "Black Box" problem. Standard chat interfaces provide answers, but for high-stakes corporate strategy—like pharmaceutical launches or payer negotiations—an answer without a visible reasoning trail is a liability, not an asset. Executives cannot bet a billion-dollar decision on a hallucination.

**coreason-maco** (Multi-Agent Collaborative Orchestrator) was built to solve this by transforming AI from a chatbot into a **"Strategic Simulator."** Known internally as *"The General,"* this engine does not merely generate text; it executes deterministic, audit-ready workflows. It treats reasoning as a visible manufacturing process rather than a magic trick.

The specific "pain point" this architecture resolves is the lack of **Architectural Triangulation** in standard LLM apps. Instead of relying on a single model, `coreason-maco` orchestrates a "Council of Models"—specialized agents that debate, verify, and synthesize findings. By forcing reasoning into a Directed Acyclic Graph (DAG), it ensures that every decision is traceable, auditable, and GxP-compliant, providing the "Glass Box" transparency required by regulated industries.

## 2. Under the Hood (The Dependencies & Logic)

The package utilizes a lean, high-performance stack chosen for strict type safety and asynchronous concurrency:

*   **`networkx` (The Brain):** The core data structure is a DiGraph (Directed Acyclic Graph). This allows `maco` to validate logical consistency, detect cycles, and strictly enforce dependency orders before a single agent is fired.
*   **`anyio` & `asyncio` (The Nervous System):** To achieve the "Council" effect, multiple agents must "think" in parallel. The engine uses `asyncio.TaskGroup` to manage concurrent execution branches, ensuring that a "Payer Persona" and a "Provider Persona" can react to a strategy simultaneously without blocking the main thread.
*   **`pydantic` (The Law):** In a GxP environment, data integrity is paramount. Every event—from a node starting to an artifact being generated—is rigorously defined as a Pydantic model (`GraphEvent`). This ensures that the "Living Canvas" UI never receives malformed telemetry.
*   **`jinja2` (The Connector):** Dynamic variable resolution allows the output of one agent (e.g., "Market Analysis") to be injected precisely into the prompt of the next (e.g., "SWOT Generator") without fragile string concatenation.

The logic is centered around the **`WorkflowRunner`**. Unlike simple chains, this runner supports **Conditional Branching** (pruning dead logic paths dynamically) and **State Snapshots**. It is stateless by design; it accepts a recipe and inputs, runs the simulation, and yields a stream of atomic events.

## 3. In Practice (The How)

### Example 1: The Happy Path
Here, we initialize the controller and stream the execution of a strategic recipe. Notice how the engine yields events in real-time, allowing for a "Living Canvas" experience.

```python
import asyncio
from coreason_maco.core.controller import WorkflowController
from coreason_maco.infrastructure.server_defaults import ServerRegistry

async def run_strategy_simulation():
    # 1. Initialize the Engine with default services (Tools, Logger, etc.)
    services = ServerRegistry()
    controller = WorkflowController(services=services)

    # 2. Define the inputs for the "War Game" recipe
    inputs = {
        "drug_name": "Xylophin",
        "competitor": "OldPharma Inc.",
        "market_segment": "Oncology"
    }

    # 3. Execute the recipe (Manifest) and stream the "thought process"
    # 'recipe_manifest' would be loaded from your config/database
    async for event in controller.execute_recipe(recipe_manifest, inputs):
        if event.event_type == "NODE_START":
            print(f"Thinking: {event.node_id} is analyzing...")
        elif event.event_type == "NODE_DONE":
            print(f"Result: {event.payload['output_summary']}")
        elif event.event_type == "EDGE_ACTIVE":
            print(f"Logic Flow: Moving from {event.payload['source']} -> {event.payload['target']}")

# Run the simulation
# asyncio.run(run_strategy_simulation())
```

### Example 2: The "Time Machine" (Resuming State)
One of `coreason-maco`'s most powerful features is **Crash Recovery**. If a long-running simulation is interrupted, you can resume exactly where it left off by passing a `resume_snapshot`.

```python
async def resume_simulation(previous_crash_snapshot):
    controller = WorkflowController(services=ServerRegistry())

    # The snapshot contains the outputs of nodes that already finished successfully.
    # The engine will skip execution for these and 'Fast Forward' to the pending nodes.
    snapshot = {
        "node_1_market_research": "The market is saturated...",
        "node_2_competitor_analysis": "Competitor X is weak in pricing..."
    }

    print("Resuming simulation from saved state...")
    async for event in controller.execute_recipe(
        recipe_manifest,
        inputs={},
        resume_snapshot=snapshot
    ):
        if event.event_type == "NODE_RESTORED":
            print(f"Skipped: {event.node_id} (Restored from cache)")
        else:
            print(f"Executing: {event.node_id} (New Work)")
```
