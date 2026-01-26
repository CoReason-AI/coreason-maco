# Compliance Report: coreason-maco

## 1. Executive Summary

This report documents the findings of the "Strict Compliance Check" performed on the `coreason-maco` package against the provided Architecture Specification (`MACO-001` and `TRD-MACO`).

The package generally adheres to the specified roles and relationships, implementing the "General" (Runtime Execution Engine) as a pure Python library with strict typing and dependency injection. However, specific violations were identified and addressed or noted.

## 2. Compliance Findings & Actions

### 2.1. Critical Violations (Refactored)

**Violation:** `WorkflowController` instantiation logic.
- **Spec:** MACO-001 Section 5, Step 3 states that `execute_recipe` must "Instantiate WorkflowRunner".
- **Implementation (Before):** `WorkflowController` instantiated `WorkflowRunner` in `__init__`, reusing the instance across executions.
- **Action:** Refactored `src/coreason_maco/core/controller.py`. `WorkflowController` now accepts a `runner_cls` (factory) in `__init__` and instantiates a fresh `WorkflowRunner` inside `execute_recipe` for each run. This ensures strict adherence to the execution flow and guarantees a clean state for every recipe execution while maintaining testability.

### 2.2. Critical Violations (Environment Constraints)

**Violation:** `RecipeManifest` definition.
- **Spec:** MACO-001 Section 5, Integration Context states: `RecipeManifest` (from `coreason-manifest`).
- **Implementation:** `RecipeManifest` is defined locally in `src/coreason_maco/core/manifest.py`. `coreason-manifest` is not listed in `pyproject.toml`.
- **Reason:** The external package `coreason-manifest` is not available in the current development environment.
- **Action:** The local definition is retained to ensure functionality. In a production environment with access to private PyPI feeds, this should be refactored to import from `coreason-manifest`.

### 2.3. Event Protocol Compliance

- **Spec:** TRD-MACO Section 2.1 defines the JSON Schema for Graph Events. MACO-001 Section 4 defines the Pydantic models.
- **Finding:** The implementation in `src/coreason_maco/events/protocol.py` follows the Pydantic models specified in MACO-001 (`visual_metadata` instead of `visuals`). This is considered compliant as MACO-001 is the "Source of Truth" for the internal data structures.
- **Visual Cues:** The `EventFactory` correctly maps event types to the required visual cues (e.g., `NODE_START` -> `PULSING`).

### 2.4. Architecture & Topology

- **Role:** `coreason-maco` correctly acts as a passive engine. It does not implement HTTP servers or database drivers.
- **Topology:** `src/coreason_maco/engine/topology.py` correctly uses `networkx` for DAG validation (acyclic, connectivity) and execution layer generation.
- **Runner:** `src/coreason_maco/engine/runner.py` correctly implements `asyncio` parallel execution (via `TaskGroup` implied logic or `asyncio.gather`), dynamic routing (branch pruning), and state resumption.

## 3. Conclusion

With the refactoring of `WorkflowController`, the `coreason-maco` package is now as compliant as possible within the current environment. The core architectural principles (Stateless, Event-Driven, Dependency Injection) are strictly enforced.
