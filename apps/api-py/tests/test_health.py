from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health_check() -> None:
    response = client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert isinstance(body["providers"]["llm"], str)
    assert isinstance(body["providers"]["embedding"], str)
    creds = body["credentials"]
    for key in (
        "cloudflare_configured",
        "gemini_configured",
        "groq_configured",
        "cerebras_configured",
        "fireworks_configured",
    ):
        assert isinstance(creds[key], bool)
