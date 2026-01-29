from typing import Any, Dict

from fastapi.testclient import TestClient

from coreason_maco.server import app

client = TestClient(app)


def test_invalid_manifest_structure() -> None:
    """Test server response when manifest is invalid (missing 'nodes')."""
    manifest: Dict[str, Any] = {
        "name": "Invalid Manifest",
        # "nodes": []  <-- Missing
        "edges": [],
    }
    inputs: Dict[str, Any] = {"trace_id": "t"}
    user_context = {
        "user_id": "u",
        "email": "u@example.com",
        "roles": [],
        "metadata": {},
    }

    response = client.post("/execute", json={"manifest": manifest, "inputs": inputs, "user_context": user_context})

    # Pydantic validation error is handled by FastAPI's default exception handler (422)
    # OR by the controller validation if it passes the Pydantic model check first.
    # In this case, `ExecuteRequest` types `manifest` as `Dict`, so basic structure passes,
    # but `WorkflowController` -> `RecipeManifest` will fail.
    # Since we wrap the controller call in a try/except block in server.py and return 500,
    # we expect 500.

    assert response.status_code == 500
    assert "Field required" in response.json()["detail"] or "nodes" in response.json()["detail"]


def test_missing_inputs() -> None:
    """Test server response when inputs are missing required fields."""
    manifest = {
        "name": "Valid Manifest",
        "nodes": [{"id": "A", "type": "LLM"}],
        "edges": [],
    }
    inputs: Dict[str, Any] = {
        # Missing trace_id
    }
    user_context = {
        "user_id": "u",
        "email": "u@example.com",
        "roles": [],
        "metadata": {},
    }

    response = client.post("/execute", json={"manifest": manifest, "inputs": inputs, "user_context": user_context})

    # Controller raises ValueError
    assert response.status_code == 500
    assert "trace_id is required" in response.json()["detail"]


def test_empty_execution() -> None:
    """Test executing an empty workflow."""
    manifest = {
        "name": "Empty Workflow",
        "nodes": [],
        "edges": [],
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
    assert data["run_id"] is None
    assert data["events"] == []
