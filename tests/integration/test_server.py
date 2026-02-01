from fastapi.testclient import TestClient

from coreason_maco.server import app

client = TestClient(app)


def test_health_check() -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}


def test_execute_workflow() -> None:
    manifest = {
        "id": "workflow-1",
        "version": "1.0.0",
        "name": "Test Workflow",
        "topology": {
            "nodes": [
                {
                    "id": "A",
                    "type": "agent",
                    "agent_name": "Writer",
                    "visual": {"x_y_coordinates": [0, 0], "label": "A", "icon": "box"}
                }
            ],
            "edges": []
        },
        "interface": {"inputs": {}, "outputs": {}},
        "state": {"schema": {}},
        "parameters": {}
    }
    inputs = {"trace_id": "test_trace"}
    user_context = {
        "user_id": "test_user",
        "email": "test@example.com",
        "roles": [],
        "metadata": {},
    }

    response = client.post("/execute", json={"manifest": manifest, "inputs": inputs, "user_context": user_context})
    assert response.status_code == 200
    data = response.json()
    assert "run_id" in data
    assert "events" in data
    assert len(data["events"]) > 0
