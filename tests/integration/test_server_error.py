from typing import Any, Dict

from fastapi.testclient import TestClient

from coreason_maco.server import app

client = TestClient(app)


def test_execute_workflow_error() -> None:
    manifest = {
        "id": "err",
        "version": "1.0.0",
        "name": "Error Workflow",
        "topology": {
            "nodes": [
                {"id": "A", "type": "agent", "agent_name": "A", "visual": {"x_y_coordinates": [0,0], "label": "A", "icon": "box"}}
            ],
            "edges": [],
        },
        "interface": {"inputs": {}, "outputs": {}},
        "state": {"schema": {}},
        "parameters": {}
    }
    # Inputs that cause a validation error or similar to trigger the exception block
    inputs: Dict[str, Any] = {
        # Missing trace_id to cause controller validation error
    }
    user_context = {
        "user_id": "u",
        "email": "u@example.com",
        "roles": [],
        "metadata": {},
    }

    response = client.post("/execute", json={"manifest": manifest, "inputs": inputs, "user_context": user_context})
    assert response.status_code == 500
    assert "trace_id is required" in response.json()["detail"]
