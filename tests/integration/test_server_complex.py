from fastapi.testclient import TestClient

from coreason_maco.server import app

client = TestClient(app)


def test_complex_workflow_execution() -> None:
    """Test a workflow with multiple nodes and dependencies."""
    manifest = {
        "id": "complex-1",
        "version": "1.0.0",
        "name": "Complex Workflow",
        "topology": {
            "nodes": [
                {
                    "id": "A",
                    "type": "agent",
                    "agent_name": "StartAgent",
                    "visual": {"x_y_coordinates": [0, 0], "label": "A", "icon": "box"},
                },
                {
                    "id": "B",
                    "type": "logic",
                    "code": "Calculator",
                    "visual": {"x_y_coordinates": [0, 0], "label": "B", "icon": "box"},
                },
                {
                    "id": "C",
                    "type": "agent",
                    "agent_name": "EndAgent",
                    "visual": {"x_y_coordinates": [0, 0], "label": "C", "icon": "box"},
                },
            ],
            "edges": [
                {"source_node_id": "A", "target_node_id": "B"},
                {"source_node_id": "B", "target_node_id": "C"},
            ],
        },
        "interface": {"inputs": {}, "outputs": {}},
        "state": {"schema": {}},
        "parameters": {},
    }
    inputs = {"trace_id": "t"}
    user_context = {
        "user_id": "u",
        "email": "u@example.com",
        "roles": [],
        "metadata": {},
    }

    response = client.post("/execute", json={"manifest": manifest, "inputs": inputs, "user_context": user_context})
    assert response.status_code == 200

    data = response.json()
    events = data["events"]

    # Analyze Event Sequence
    assert len(events) > 0

    # 1. Initialization
    init_events = [e for e in events if e["event_type"] == "NODE_INIT"]
    assert len(init_events) == 3

    # 2. Execution order
    completed_nodes = [e["node_id"] for e in events if e["event_type"] == "NODE_DONE"]

    # A -> B -> C (Basic check, though parallelism might affect exact order of adjacent non-dependent nodes,
    # here they are strictly dependent)
    assert "A" in completed_nodes
    assert "B" in completed_nodes
    assert "C" in completed_nodes

    # Verify strict order A -> B -> C
    idx_a = completed_nodes.index("A")
    idx_b = completed_nodes.index("B")
    idx_c = completed_nodes.index("C")

    assert idx_a < idx_b < idx_c

    # 3. Check for Artifact Generation (from Tool)
    # The Mock ServerToolExecutor returns a dict, but doesn't explicitly return an 'artifact' structure
    # unless we change the mock. The current mock returns {"status": "executed"...}
    # So we just verify the tool node completed successfully.

    b_completion = next(e for e in events if e["event_type"] == "NODE_DONE" and e["node_id"] == "B")
    assert "Server execution placeholder" in b_completion["payload"]["output_summary"]
