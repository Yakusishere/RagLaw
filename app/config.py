from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env.local",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    database_url: str = "postgresql://law:change-me@localhost:5432/law_helper"
    openai_api_key: str = ""
    openai_chat_model: str = "gpt-4.1-mini"
    openai_embedding_model: str = "text-embedding-3-small"
    retrieval_vector_top_k: int = 12
    retrieval_keyword_top_k: int = 12
    retrieval_final_top_k: int = 8


@lru_cache
def get_settings() -> Settings:
    return Settings()
