# Core Concepts: MACO vs. Agents

## Executive Summary
The CoReason platform bifurcates intelligence into two distinct layers: **MACO**, the stateful orchestrator responsible for strategy and governance, and **Agents**, the stateless atomic units responsible for executing specific tactical tasks. This separation ensures that complex workflows are auditable, governable, and resilient, while individual capabilities remain modular and testable.

## The "General vs. Soldier" Metaphor

To understand the architecture, consider a military command structure:

*   **MACO (The General):** The General does not fire a rifle. Instead, the General assesses the battlefield map (the State), decides on a strategy (the Recipe), and issues orders. The General is responsible for the overall success of the mission, ensuring rules of engagement (Governance) are followed, and adjusting plans if a flank collapses (What-If Forking).
*   **Agent (The Soldier):** The Soldier is a specialist trained to execute a specific order perfectly, such as "secure this hill" or "defuse this mine." The Soldier does not question the broader strategy or need to know the status of the entire army. They receive an input, perform their duty (Logic), and report back the result.

In CoReason, MACO holds the context and directs the flow; Agents perform the work without carrying the burden of state.

## Comparative Table

| Feature | MACO (Multi-Agent Collaborative Orchestrator) | Agent (Atomic Unit of Capability) |
| :--- | :--- | :--- |
| **Scope** | Global / Strategic | Local / Tactical |
| **State Awareness** | **Stateful:** Aware of the entire Graph history, context, and potential future paths. | **Stateless:** Aware only of its immediate input and output. |
| **Logic Type** | **DAG (Directed Acyclic Graph):** Non-linear, conditional, and multi-threaded. | **Linear:** Procedural, step-by-step execution of a single task. |
| **Responsibility** | Governance, Orchestration, Audit Logging, Error Recovery, Branching. | Execution of business logic (e.g., API calls, Data Processing, LLM Inference). |
| **Analogy** | Conductor of an Orchestra | First Violinist |

## Interaction Flow

The following pseudo-code illustrates how a `Recipe` (MACO) invokes an `Agent`. Note that MACO manages the flow and data passing, while the Agent remains a black box function.

```python
# MACO Context (The Orchestrator)
class WorkflowEngine:
    def execute_step(self, context, node_id):
        # 1. Resolve Inputs based on Graph State
        inputs = self.resolve_inputs(node_id, context.history)

        # 2. Check Governance (The Council)
        if not self.council.approve(inputs):
            return self.handle_rejection(node_id)

        # 3. Delegate to Agent (The "Soldier")
        # MACO waits here; logic is external
        result = AgentRegistry.invoke(
            agent_name="ClinicalTrialExtractAgent",
            payload=inputs
        )

        # 4. Update State and Audit Log
        context.update_history(node_id, result)
        self.audit_logger.log(node_id, inputs, result)

        # 5. Determine Next Step (DAG Traversal)
        next_nodes = self.graph.get_successors(node_id, result)
        return next_nodes

# Agent Context (The Atomic Unit)
def ClinicalTrialExtractAgent(payload: dict) -> dict:
    """
    Pure functional logic.
    No awareness of 'WorkflowEngine' or 'History'.
    """
    pdf_content = payload.get("pdf_stream")

    # Linear, procedural work
    text = extract_text(pdf_content)
    adverse_events = nlp_model.find_events(text)

    return {"adverse_events": adverse_events}
```
