# CoReason Runtime Engine ("The General")

**Multi-Agent Collaborative Orchestrator (MACO)**

[![License: Prosperity 3.0](https://img.shields.io/badge/License-Prosperity%203.0-blue.svg)](https://github.com/CoReason-AI/coreason_maco/blob/main/LICENSE)
[![CI/CD](https://github.com/CoReason-AI/coreason_maco/actions/workflows/ci-cd.yml/badge.svg)](https://github.com/CoReason-AI/coreason_maco/actions/workflows/ci-cd.yml)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/CoReason-AI/coreason_maco/blob/main/pyproject.toml)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/CoReason-AI/coreason_maco)

## Overview

**`coreason-maco`** is the runtime engine designed to transform AI from a "Chatbot" into a **"Strategic Simulator."** It executes pre-defined, deterministic workflows ("Recipes") where multiple specialized AI agents collaborate, debate, and verify each other's work.

As the **Orchestrator**, it manages a team of specialized agents to break down complex problems, execute parallel research streams, debate findings using a "Council of Models", and visualize the entire thought process in real-time.

## Key Features

*   **"Glass Box" Visualization:** Exposes internal state in real-time. Users can see exactly which agent is working, what data they are accessing, and where they are in the process.
*   **Architectural Triangulation ("The Council"):** Automatically "triangulates" answers by asking distinct models (e.g., OpenAI, Anthropic, DeepSeek) and synthesizing consensus to reduce hallucination.
*   **Counterfactual Simulation ("What-If" Analysis):** Allows users to "Fork" the reasoning process to explore different scenarios without losing original data.
*   **GxP Compliance & Determinism:** Ensures workflows are reproducible. Running the same "Recipe" with the same inputs and "Seed" yields the exact same result.

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
    async for event in controller.execute_recipe(manifest, inputs):
        print(f"Event: {event.event_type} | Node: {event.node_id} | Payload: {event.payload}")

if __name__ == "__main__":
    asyncio.run(main())
```

## Requirements

*   Python 3.12+
*   `pydantic>=2.0`
*   `networkx`
*   `anyio`
