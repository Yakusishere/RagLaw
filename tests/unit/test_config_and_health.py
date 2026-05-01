from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app


def test_settings_reads_environment(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql://law:pass@localhost:5432/law_helper")
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    settings = Settings()
    assert settings.database_url == "postgresql://law:pass@localhost:5432/law_helper"
    assert settings.openai_api_key == "test-key"
    assert settings.retrieval_final_top_k == 8


def test_health_endpoint_returns_ok():
    client = TestClient(create_app())
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
