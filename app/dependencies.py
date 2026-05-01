from collections.abc import Iterator

from fastapi import Depends
from openai import OpenAI
from psycopg import Connection

from app.config import Settings, get_settings
from app.db.connection import get_connection
from app.db.repositories.retrieval_repository import RetrievalRepository
from app.services.retrieval_service import RetrievalService


def get_app_settings() -> Settings:
    return get_settings()


def get_db_connection() -> Iterator[Connection]:
    with get_connection() as conn:
        yield conn


class OpenAIEmbeddingClient:
    def __init__(self, api_key: str, model_name: str):
        self._client = OpenAI(api_key=api_key)
        self._model_name = model_name

    def embed_query(self, query: str) -> list[float]:
        response = self._client.embeddings.create(model=self._model_name, input=query)
        return response.data[0].embedding


def get_retrieval_service(
    settings: Settings = Depends(get_app_settings),
    conn: Connection = Depends(get_db_connection),
) -> RetrievalService:
    repository = RetrievalRepository(conn)
    embedding_client = OpenAIEmbeddingClient(
        settings.openai_api_key,
        settings.openai_embedding_model,
    )
    return RetrievalService(repository, embedding_client, settings)
