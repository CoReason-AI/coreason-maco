# CoReason Runtime Engine ("The General")

**Multi-Agent Collaborative Orchestrator (MACO)**

[![License: Prosperity 3.0](https://img.shields.io/badge/license-Prosperity%203.0-blue)](LICENSE)
[![CI/Status](https://github.com/CoReason-AI/coreason_maco/actions/workflows/ci.yml/badge.svg)](https://github.com/CoReason-AI/coreason_maco/actions)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)
[![Documentation](https://img.shields.io/badge/docs-product%20requirements-blue)](docs/product_requirements.md)

## Overview

**`coreason-maco`** is the runtime engine designed to transform AI from a "Chatbot" into a **"Strategic Simulator."** It executes pre-defined, deterministic workflows ("Recipes") where multiple specialized AI agents collaborate, debate, and verify each other's work.

As the **Orchestrator**, it manages a team of specialized agents to:
*   **Break down** complex problems into steps.
*   **Execute** parallel research streams.
*   **Debate** findings using a "Council of Models" (Architectural Triangulation).
*   **Visualize** the entire thought process in real-time.

## Features

*   **"Glass Box" Visualization:** Exposes internal state in real-time. Users can see exactly which agent is working, what data they are accessing, and where they are in the process.
*   **Architectural Triangulation ("The Council"):** Automatically "triangulates" answers by asking three distinct models (e.g., OpenAI, Anthropic, DeepSeek) and having a fourth "Judge" agent synthesize the consensus.
*   **Counterfactual Simulation ("What-If" Analysis):** Allows users to "Fork" the reasoning process to explore different scenarios without losing original data.
*   **GxP Compliance & Determinism:** Ensures workflows are reproducible. Running the same "Recipe" with the same inputs and "Seed" yields the exact same result.
*   **Secure Identity Propagation:** Propagates `UserContext` (Identity Passport) securely to all workers and tools, ensuring "On-Behalf-Of" execution without leaking tokens in UI events.

## Installation

```bash
pip install coreason_maco
```

## Usage

Here is how to initialize and execute a workflow using `coreason-maco`:

```python
import asyncio
from coreason_maco.core.controller import WorkflowController
from coreason_maco.infrastructure.server_defaults import ServerRegistry

# Optional: Import UserContext if available
try:
    from coreason_identity.models import UserContext
except ImportError:
    UserContext = None

async def main():
    # 1. Initialize Services (Dependency Injection)
    services = ServerRegistry()

    # 2. Initialize Controller
    controller = WorkflowController(services=services)

    # 3. Define a Simple Manifest (Recipe)
    manifest = {
        "name": "Simple Greeting",
        "nodes": [
            {"id": "node_1", "type": "LLM", "config": {"prompt": "Say hello!"}}
        ],
        "edges": []
    }

    # 4. Define Inputs
    inputs = {
        "user_id": "test_user",
        "trace_id": "trace_123",
        "secrets_map": {}
    }

    # 5. Execute Workflow
    print("Starting Workflow...")
    # Pass user_context (Optional)
    async for event in controller.execute_recipe(manifest, inputs, user_context=None):
        print(f"Event: {event.event_type} | Node: {event.node_id} | Payload: {event.payload}")

if __name__ == "__main__":
    asyncio.run(main())
```
