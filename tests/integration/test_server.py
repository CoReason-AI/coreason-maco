from fastapi.testclient import TestClient

from coreason_maco.server import app

client = TestClient(app)


def test_health_check() -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}


def test_execute_workflow() -> None:
    manifest = {"name": "Test Workflow", "nodes": [{"id": "A", "type": "LLM"}], "edges": []}
    inputs = {"user_id": "test_user", "trace_id": "test_trace"}

    response = client.post("/execute", json={"manifest": manifest, "inputs": inputs})
    assert response.status_code == 200
    data = response.json()
    assert "run_id" in data
    assert "events" in data
    assert len(data["events"]) > 0
