# **BRD-MACO: Multi-Agent Collaborative Orchestrator**

**Project Name:** CoReason Runtime Engine ("The General")
**Target Audience:** Corporate Strategy, Market Access, and Medical Affairs Teams
**Business Impact:** High (Core Platform Differentiator)

---

## **1. Executive Summary**

Current Generative AI solutions are "Black Boxes"—they take a prompt and output a result with no visibility into the intermediate reasoning. In highly regulated industries like Biopharma, this opacity is unacceptable for strategic decision-making.

**`coreason-maco`** is the runtime engine designed to solve this. It transforms AI from a "Chatbot" into a **"Strategic Simulator."** It executes pre-defined, deterministic workflows ("Recipes") where multiple specialized AI agents collaborate, debate, and verify each other's work.

**The Business Goal:** To provide a **"Glass Box"** reasoning engine that allows executives to run complex simulations (e.g., "Payer War Games", "Launch Pricing Scenarios") with total transparency, auditability, and control.

---

## **2. Problem Statement & Opportunity**

### **The Problem**

1. **Hallucination Risk:** A single LLM often fabricates facts. Strategy teams cannot trust a $1B launch decision to a single model.
2. **Lack of Auditability:** Standard chat interfaces do not leave a GxP-compliant audit trail of *why* a decision was recommended.
3. **Linear Thinking:** Real-world problems are non-linear (Directed Acyclic Graphs), requiring branching logic and parallel processing, which standard chatbots cannot handle.

### **The Solution (MACO)**

`coreason-maco` acts as the **Orchestrator**. It does not just "answer"; it manages a team of specialized agents to:

* **Break down** complex problems into steps.
* **Execute** parallel research streams.
* **Debate** findings using a "Council of Models" (Architectural Triangulation).
* **Visualize** the entire thought process in real-time.

---

## **3. Key Business Requirements (The "Must Haves")**

### **BR-01: The "Glass Box" Visualization**

* **Requirement:** The system must expose its internal state to the user in real-time.
* **User Experience:** As the AI thinks, the user sees a visual map (The Living Canvas) lighting up. They can see exactly which agent is working, what data they are accessing, and where they are in the process.
* **Success Metric:** User trust scores increase by 40% compared to standard chat interfaces.

### **BR-02: Architectural Triangulation (The "Council")**

* **Requirement:** Critical decisions must never rely on a single Model (e.g., just GPT-4).
* **Logic:** The system must automatically "triangulate" answers by asking three distinct models (e.g., OpenAI, Anthropic, DeepSeek) and having a fourth "Judge" agent synthesize the consensus.
* **Value:** Drastically reduces hallucination and bias.

### **BR-03: Counterfactual Simulation ("What-If" Analysis)**

* **Requirement:** Users must be able to "Fork" the reasoning process.
* **User Experience:** A user can pause the simulation at Step 5 and ask, *"What if we changed the price from $500 to $700?"* The engine must branch off a new parallel reality without losing the original data.

### **BR-04: GxP Compliance & Determinism**

* **Requirement:** The workflow must be reproducible.
* **Constraint:** If I run the same "Recipe" with the same inputs and the same "Seed," I must get the exact same result. This is critical for regulatory audits.

---

## **4. User Stories**

| ID | As A... | I Want To... | So That... |
| --- | --- | --- | --- |
| **US-1** | **Strategy Lead** | Run a "Payer Negotiation War Game" | I can anticipate objections from insurance companies before we launch. |
| **US-2** | **Compliance Officer** | See exactly which documents the AI used to make a claim | I can verify that no off-label marketing material was referenced. |
| **US-3** | **Market Access VP** | Pause the simulation and inject a new competitor into the scenario | I can see how our strategy holds up against unexpected market shifts. |
| **US-4** | **Data Scientist** | Swap out the underlying LLM (e.g., Llama 3 for GPT-4) without rewriting code | I can optimize for cost vs. accuracy. |

---

## **5. Integration Context**

To function, `coreason-maco` sits at the center of the ecosystem:

* **Inputs:** It receives a **Strategic Recipe** (from `coreason-manifest`) and User Context (from `coreason-api`).
* **Resources:** It "hires" workers (Agents) from `coreason-cortex` and gives them tools from `coreason-mcp`.
* **Outputs:** It streams **Live Telemetry** (Graph Events) to the Flutter UI and writes a final **Audit Log** to `coreason-veritas`.

---

## **6. Success Metrics (KPIs)**

1. **Orchestration Latency:** The overhead of the graph engine (managing the nodes) must be <50ms per step. (The *agents* can be slow, but the *manager* must be fast).
2. **Resiliency:** 99.9% successful recovery from API timeouts. If an agent fails, MACO must auto-retry or degrade gracefully.
3. **Visualization Fidelity:** The Frontend must receive status updates within 200ms of the backend state change to ensure the animation feels "live."

---

## **7. Glossary**

* **Recipe:** A pre-defined workflow template (e.g., "Launch Readiness Assessment").
* **Agent:** A specialized worker node (e.g., "The Medical Writer", "The Statistician").
* **Council:** A group of agents debating to find the truth.
* **Living Canvas:** The interactive map where users watch the work happen.
MACO-001: Coreason Multi-Agent Collaborative Orchestrator**

**Target Package:** `coreason-maco`
**Architecture Standard:** GxP-Compliant, Event-Driven, Async-First
**Role:** The "General" (Runtime Execution Engine)

---

## **1. System Identity & Mission**

You are building the **Central Nervous System** of the CoReason platform.
`coreason-maco` is a **pure Python library** responsible for loading a "Strategic Recipe" (a Directed Acyclic Graph), executing it by orchestrating sub-agents (`coreason-cortex`), and broadcasting real-time telemetry to the "Living Canvas" UI.

**The Golden Rule:** `coreason-maco` **NEVER** speaks directly to the outside world.

* It does **NOT** run an HTTP server (that is `coreason-api`).
* It does **NOT** connect to Redis (that is injected).
* It is a **passive engine** that waits to be invoked.

---

## **2. Architectural Constraints (Immutable Laws)**

1. **Async Generators for Telemetry (The "Pulse"):**
* The main execution method `run_workflow()` **MUST** return an `AsyncGenerator`.
* It yields `GraphEvent` objects in real-time. This allows the host (`coreason-api`) to stream updates via SSE/Redis without `maco` needing to know about the transport layer.


2. **Dependency Injection Only:**
* You cannot import `coreason_identity` or `coreason_mcp` directly to fetch data.
* All external capabilities (Tools, Loggers, Auth Context) must be passed into the `WorkflowEngine` constructor.


3. **State Recovery (The "Pause" Button):**
* Every step execution must yield a **State Snapshot**.
* The engine must be able to accept a `resume_from_state` payload to restart a crashed workflow from the last successful node.


4. **Strict Typing:**
* 100% Type Hints.
* Pydantic V2 for all data structures.



---

## **3. Functional Requirements (The Core Modules)**

### **Module A: The Graph Topology (`src/core/topology.py`)**

**Goal:** In-memory representation and validation of the Strategic Recipe.

1. **DAG Validation:**
* **Input:** `RecipeManifest` (from `coreason-manifest`).
* **Logic:** Use `networkx` to build a DiGraph.
* **Constraint:** Validate the graph is **Acyclic**. Detect and reject "Islands" (disconnected nodes).


2. **Topological Execution Order:**
* Determine the sequence. Identify parallel branches (e.g., Node B and Node C depend only on Node A).



### **Module B: The Workflow Engine (`src/engine/runner.py`)**

**Goal:** The main loop that iterates through the DAG.

1. **Method Signature:**
```python
async def run_workflow(
    self,
    recipe: RecipeManifest,
    context: ExecutionContext
) -> AsyncGenerator[GraphEvent, None]:

```


2. **Parallel Execution:**
* If Node A splits into Node B and Node C, the Engine must create `asyncio.create_task` for both B and C and await them concurrently.


3. **Dynamic Routing (The "Switch"):**
* Support `ConditionalNode`. Based on the output of Node A (e.g., `risk_score > 50`), the engine must dynamically prune the "Low Risk" branch and only traverse the "High Risk" edges.



### **Module C: The "Living Canvas" Protocol (`src/events/protocol.py`)**

**Goal:** Structure the visual cues for the Flutter UI.

**Requirement:** Unlike standard logs, these events drive UI animations.

1. **Event Schema:** You must define these Pydantic models:
* `NodeStarted`: `{ node_id, timestamp, status="RUNNING", visual_cue="PULSE" }`
* `NodeCompleted`: `{ node_id, output_summary, status="SUCCESS", visual_cue="GREEN_GLOW" }`
* `EdgeTraversed`: `{ source, target, animation_speed="FAST" }`
* `ArtifactGenerated`: `{ node_id, artifact_type="PDF", url="..." }`



### **Module D: The Council Logic (`src/strategies/council.py`)**

**Goal:** Orchestrate multi-model consensus ("Architectural Triangulation").

1. **Pattern:** Map-Reduce.
* **Map:** Fan out the prompt to N agents (e.g., Llama 3, GPT-4, Claude).
* **Reduce:** Feed all N responses into a "Synthesizer Agent" to generate a final consensus.


2. **Constraint:** This complex logic must appear as a single "Super Node" in the graph execution stream.

---

## **4. Data Structures (Pydantic Specifications)**

The agent must implement the following schemas immediately to satisfy the "Living Canvas" requirement:

```python
# src/schemas/events.py
from pydantic import BaseModel, Field
from typing import Literal, Any, Dict

class GraphEvent(BaseModel):
    """
    The atomic unit of communication between the Engine (MACO)
    and the UI (Flutter).
    """
    event_type: Literal["NODE_START", "NODE_END", "EDGE_TRAVERSAL", "ERROR"]
    run_id: str
    node_id: str
    timestamp: float

    # The payload contains the actual reasoning/data
    payload: Dict[str, Any] = Field(..., description="The logic output")

    # Visual Metadata drives the Flutter animation engine
    visual_metadata: Dict[str, str] = Field(
        ...,
        description="Hints for UI: color='#00FF00', animation='pulse', progress='0.5'"
    )

class ExecutionContext(BaseModel):
    """
    The Context Injection Object.
    Prevents MACO from needing direct access to Auth or DB drivers.
    """
    user_id: str
    trace_id: str
    secrets_map: Dict[str, str]  # Decrypted secrets passed from Vault
    tool_registry: Any           # Interface for coreason-mcp (The Tools)

```

---

## **5. Execution Plan for the Autonomous Agent**

**Step 1: Scaffolding**

* Initialize `pyproject.toml` with dependencies: `pydantic>=2.0`, `networkx`, `anyio`.
* Create directory structure: `src/core`, `src/engine`, `src/events`, `tests`.

**Step 2: The Event Protocol (Priority 1)**

* Implement `src/events/protocol.py` first. This defines the contract. Without this, the engine is mute.

**Step 3: The Engine Logic**

* Implement the `WorkflowRunner` class.
* **Unit Test:** Write a test with a mock DAG (A -> B -> C). Verify the `AsyncGenerator` yields exactly 6 events (Start A, End A, Start B, End B...).

**Step 4: Branching Logic**

* Implement `ConditionalRouter`.
* **Unit Test:** Create a graph where Node A returns "False". Ensure Node C (True path) is *never* executed.

**Step 5: Error Handling & Resume**

* Implement `try/except` blocks around `node.execute()`.
* On error, yield a `WorkflowError` event containing the stack trace and the state snapshot of the inputs that caused the crash.

---

## **6. Success Criteria (Definition of Done)**

1. **The "Visual" Test:**
* Running the package locally with a test script produces a stream of JSON logs that clearly narrate the story of the execution (e.g., "Node A thinking...", "Node A finished", "Moving to Node B").


2. **The Concurrency Test:**
* A graph with two parallel "sleep(1s)" nodes finishes in ~1.1 seconds, not 2.0 seconds.


3. **The Import Test:**
* `from coreason_maco import WorkflowRunner` works without error.
* No hard dependencies on `flask`, `fastapi`, or `requests` exist in the code.
# **TRD-MACO: Technical Implementation Specification**

**Component:** `coreason-maco` (Multi-Agent Collaborative Orchestrator)
**Type:** Python Library (Stateless)
**Python Version:** 3.11+
**Dependencies:** `networkx`, `pydantic>=2.0`, `anyio`

---

## **1. Core Class Architecture**

The package must adhere to a strict **Controller-Engine-Interface** pattern to ensure testability and separation of concerns.

### **1.1. The Entry Point: `WorkflowController**`

* **Path:** `src/core/controller.py`
* **Role:** The public API surface. It accepts the raw Manifest and Context, initializes the engine, and returns the event stream.
* **Signature:**
```python
class WorkflowController:
    def __init__(self, services: ServiceRegistry):
        """
        Dependency Injection container.
        :param services: Contains AuthManager, AuditLogger, ToolRegistry.
        """
        pass

    async def execute_recipe(
        self,
        manifest: dict,
        inputs: dict
    ) -> AsyncGenerator[GraphEvent, None]:
        """
        1. Validates Manifest via coreason-manifest.
        2. Builds the DAG via TopologyEngine.
        3. Instantiates WorkflowRunner.
        4. Yields events from runner.run().
        """
        pass

```



### **1.2. The Graph Builder: `TopologyEngine**`

* **Path:** `src/engine/topology.py`
* **Role:** Wraps `networkx` to handle graph logic.
* **Key Methods:**
* `validate_acyclic(graph: nx.DiGraph) -> bool`: Raises `CyclicDependencyError` if a loop is detected.
* `get_execution_layers(graph) -> List[List[NodeID]]`: Returns a list of "generations."
* *Example:* `[[A], [B, C], [D]]` means A runs first; then B and C run in parallel; then D runs.





### **1.3. The Execution Loop: `WorkflowRunner**`

* **Path:** `src/engine/runner.py`
* **Algorithm:**
* Use `asyncio.TaskGroup` (Python 3.11+) to manage parallel branches.
* Maintain a `state_map: Dict[NodeID, NodeOutput]` to pass data between nodes.
* **Logic:**
```python
async def run(self):
    layers = topology.get_execution_layers()
    for layer in layers:
        async with asyncio.TaskGroup() as tg:
            for node_id in layer:
                if self.should_skip(node_id): continue
                tg.create_task(self.execute_node(node_id))
        # Barrier: Wait for all tasks in layer to complete before moving next.

```





---

## **2. The Graph Event Protocol (JSON Schema)**

This is the strict contract for the "Living Canvas" (Flutter UI). Every event yielded must validate against this schema.

### **2.1. Base Event Object**

```json
{
  "trace_id": "uuid-v4",
  "run_id": "uuid-v4",
  "timestamp": "ISO-8601 UTC",
  "sequence_id": 101,
  "event_type": "ENUM",
  "payload": {},
  "visuals": {}
}

```

### **2.2. Event Types & Visual Cues**

| Event Type | Payload Data | Visual Metadata (Flutter Hint) |
| --- | --- | --- |
| `NODE_INIT` | `{ "node_id": "A", "type": "LLM" }` | `{ "state": "IDLE", "color": "#GREY" }` |
| `NODE_START` | `{ "input_tokens": 1024 }` | `{ "state": "PULSING", "anim": "BREATHE" }` |
| `NODE_STREAM` | `{ "chunk": "The patient..." }` | `{ "overlay": "TEXT_BUBBLE" }` |
| `NODE_DONE` | `{ "output": "...", "cost": 0.02 }` | `{ "state": "SOLID", "color": "#GREEN" }` |
| `EDGE_ACTIVE` | `{ "from": "A", "to": "B" }` | `{ "flow_speed": "FAST", "particle": "DOT" }` |
| `COUNCIL_VOTE` | `{ "votes": {"GPT4": "Yes", "Claude": "No"} }` | `{ "widget": "VOTING_BOOTH" }` |

---

## **3. Critical Algorithms**

### **3.1. Conditional Pruning (The "Switch")**

When a `ConditionalNode` executes, it returns a decision (e.g., `"path_a"`).

* **Requirement:** The engine must immediately mark all nodes in the `"path_b"` branch as `SKIPPED`.
* **Implementation:**
1. Get all successors of the current node.
2. Check edge attributes (e.g., `edge.condition == "path_b"`).
3. If condition fails, perform a recursive Depth-First Search (DFS) on that branch to add IDs to the `skip_set`.



### **3.2. State Resume (Crash Recovery)**

* **Requirement:** If the pod crashes at Node C, we must not re-run Node A and B.
* **Mechanism:**
* Input: `resume_snapshot: Dict[NodeID, Result]`.
* On Start:
1. Load Graph.
2. For each node, check if `node_id` exists in `resume_snapshot`.
3. If Yes: Mark as `COMPLETED`, populate memory, emit `NODE_RESTORED` event (Visual: Instant Green).
4. If No: Schedule for execution.





---

## **4. Integration Interfaces**

`coreason-maco` does not exist in a vacuum. It interacts with these specific interfaces.

### **4.1. The Tool Interface (`coreason-mcp`)**

The Engine must accept a generic `ToolExecutor`.

```python
class ToolExecutor(Protocol):
    async def execute(self, tool_name: str, args: dict) -> ToolResult: ...

```

* *Why:* Keeps `maco` clean of database drivers.

### **4.2. The Agent Interface (`coreason-cortex`)**

The Engine delegates actual "thinking" to Cortex.

```python
class AgentExecutor(Protocol):
    async def invoke(self, prompt: str, model_config: dict) -> AgentResponse: ...

```

---

## **5. Performance & Non-Functional Requirements**

### **5.1. Overhead Latency**

* **Constraint:** The time between `NODE_A_END` and `NODE_B_START` (the orchestration overhead) must be **< 50ms**.
* **Implication:** Graph traversal must be CPU-efficient. Avoid heavy serialization between internal steps.

### **5.2. Concurrency Limits**

* **Constraint:** The user must be able to define `max_parallel_agents`.
* **Implementation:** Use `asyncio.Semaphore(limit)` injected into the Runner to prevent spinning up 100 LLM calls simultaneously and hitting rate limits.

### **5.3. Memory Footprint**

* **Constraint:** Large artifacts (e.g., a 10MB PDF generated by Node A) should not be held in Python memory if not needed by Node B.
* **Implementation:** Store artifacts in `coreason-foundry` (Blob Storage) and pass only the `artifact_id` reference in the Graph State.

---

## **6. Testing Strategy**

### **6.1. Unit Tests (`tests/unit/`)**

* **`test_topology.py`**: Feed it a cyclic graph (A->B->A). Assert it raises `ValidationException`.
* **`test_runner.py`**: Feed it a graph of "Mock Agents" that simply return `f"echo {input}"`. Assert the final output combines them correctly.

### **6.2. Integration Tests (`tests/integration/`)**

* **`test_resume_logic.py`**:
1. Run a 5-step workflow.
2. Kill it at step 3.
3. Pass the state to a new runner.
4. Assert Step 1 and 2 are skipped, and Step 3 resumes.
