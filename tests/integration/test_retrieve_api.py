from fastapi.testclient import TestClient

from app.dependencies import get_retrieval_service
from app.main import create_app
from app.schemas.retrieval import RetrievalResponse
from app.services.exceptions import UpstreamDependencyError


class FakeRetrievalService:
    def retrieve(self, query: str, top_k: int | None = None) -> RetrievalResponse:
        return RetrievalResponse(query=query, results=[])


class FakeFailingRetrievalService:
    def retrieve(self, query: str, top_k: int | None = None) -> RetrievalResponse:
        raise UpstreamDependencyError()


def test_retrieve_returns_empty_results_with_dependency_override():
    app = create_app()
    app.dependency_overrides[get_retrieval_service] = lambda: FakeRetrievalService()

    client = TestClient(app)
    response = client.post("/retrieve", json={"query": "商家拒绝退款怎么办"})

    assert response.status_code == 200
    assert response.json()["results"] == []


def test_retrieve_returns_502_when_upstream_dependency_call_fails():
    app = create_app()
    app.dependency_overrides[get_retrieval_service] = lambda: FakeFailingRetrievalService()

    client = TestClient(app)
    response = client.post("/retrieve", json={"query": "商家拒绝退款怎么办"})

    assert response.status_code == 502
    assert response.json() == {"detail": "上游依赖调用失败"}
