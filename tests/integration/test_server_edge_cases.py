from typing import Any, Dict

from fastapi.testclient import TestClient

from coreason_maco.server import app

client = TestClient(app)


def test_invalid_manifest_structure() -> None:
    """Test server response when manifest is invalid (missing 'topology')."""
    manifest: Dict[str, Any] = {
        "id": "invalid",
        "version": "1.0.0",
        "name": "Invalid Manifest",
        # "topology": ... <-- Missing
        "interface": {},
        "state": {},
        "parameters": {},
    }
    inputs: Dict[str, Any] = {"trace_id": "t"}
    user_context = {
        "user_id": "u",
        "email": "u@example.com",
        "roles": [],
        "metadata": {},
    }

    response = client.post("/execute", json={"manifest": manifest, "inputs": inputs, "user_context": user_context})

    assert response.status_code == 500
    detail = response.json()["detail"]
    assert "Field required" in detail or "topology" in detail


def test_missing_inputs() -> None:
    """Test server response when inputs are missing required fields."""
    manifest = {
        "id": "valid",
        "version": "1.0.0",
        "name": "Valid Manifest",
        "topology": {
            "nodes": [
                {
                    "id": "A",
                    "type": "agent",
                    "agent_name": "A",
                    "visual": {"x_y_coordinates": [0, 0], "label": "A", "icon": "box"},
                }
            ],
            "edges": [],
        },
        "interface": {"inputs": {}, "outputs": {}},
        "state": {"schema": {}},
        "parameters": {},
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
        "id": "empty",
        "version": "1.0.0",
        "name": "Empty Workflow",
        "topology": {
            "nodes": [],
            "edges": [],
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
    assert data["run_id"] is None
    assert data["events"] == []
