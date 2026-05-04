from collections.abc import Iterator
from functools import lru_cache

from fastapi import Depends
from openai import OpenAI
from psycopg import Connection

from app.config import Settings, get_settings
from app.db.connection import get_connection
from app.db.repositories.retrieval_repository import RetrievalRepository
from app.services.exceptions import UpstreamDependencyError
from app.services.draft_service import DraftService
from app.services.llm_service import LLMService
from app.services.retrieval_service import RetrievalService
from app.services.template_service import FileTemplateService


def get_app_settings() -> Settings:
    return get_settings()


def get_db_connection() -> Iterator[Connection]:
    with get_connection() as conn:
        yield conn


class OpenAIEmbeddingClient:
    def __init__(
        self,
        api_key: str,
        model_name: str,
        base_url: str | None = None,
        client: OpenAI | None = None,
    ):
        self._client = client or OpenAI(api_key=api_key, base_url=base_url)
        self._model_name = model_name

    def embed_query(self, query: str) -> list[float]:
        try:
            response = self._client.embeddings.create(model=self._model_name, input=query)
        except Exception as exc:
            raise UpstreamDependencyError() from exc
        return response.data[0].embedding


def get_retrieval_service(
    settings: Settings = Depends(get_app_settings),
    conn: Connection = Depends(get_db_connection),
) -> RetrievalService:
    repository = RetrievalRepository(conn)
    embedding_client = OpenAIEmbeddingClient(
        settings.openai_api_key,
        settings.openai_embedding_model,
        settings.openai_base_url,
    )
    return RetrievalService(repository, embedding_client, settings)


def get_chat_service(
    settings: Settings = Depends(get_app_settings),
) -> LLMService:
    return LLMService(
        settings.openai_api_key,
        settings.openai_chat_model,
        settings.openai_base_url,
    )


@lru_cache
def get_template_service() -> FileTemplateService:
    return FileTemplateService()


def get_draft_service(
    template_service: FileTemplateService = Depends(get_template_service),
    retrieval_service: RetrievalService = Depends(get_retrieval_service),
    llm_service: LLMService = Depends(get_chat_service),
) -> DraftService:
    return DraftService(template_service, retrieval_service, llm_service)
