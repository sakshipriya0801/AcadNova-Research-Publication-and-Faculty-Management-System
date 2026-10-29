"""Application configuration loaded from environment variables."""

from functools import lru_cache
from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings populated from environment variables / .env file."""

    app_name: str = "AcadNova"
    app_env: str = "development"
    app_debug: bool = True

    backend_host: str = "0.0.0.0"
    backend_port: int = 8000

    mongodb_uri: str = "mongodb://localhost:27017"
    mongodb_database: str = "research_faculty_db"
    mongodb_connect_timeout_ms: int = 5000
    mongodb_server_selection_timeout_ms: int = 5000

    # JWT authentication. ``jwt_secret_key`` is intentionally required (no
    # default) so a secret is never hard-coded in the source.
    jwt_secret_key: str
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60

    # New faculty self-registrations require administrator approval before they
    # can sign in.  Tests disable this so existing register-then-login flows
    # remain green; the production default is True.
    require_registration_approval: bool = True

    # External scholarly sources (public APIs; no secrets hard-coded).
    crossref_api_url: str = "https://api.crossref.org"
    crossref_timeout_seconds: float = 10.0

    pubmed_api_url: str = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
    pubmed_timeout_seconds: float = 10.0
    pubmed_api_key: Optional[str] = None
    pubmed_email: Optional[str] = None

    orcid_api_url: str = "https://pub.orcid.org/v3.0"
    orcid_timeout_seconds: float = 10.0
    orcid_client_id: Optional[str] = None
    orcid_client_secret: Optional[str] = None

    scopus_api_url: str = "https://api.elsevier.com/content"
    scopus_timeout_seconds: float = 10.0
    scopus_api_key: Optional[str] = None

    web_of_science_api_url: str = "https://api.clarivate.com/apis/wos-starter/v1"
    web_of_science_timeout_seconds: float = 10.0
    web_of_science_api_key: Optional[str] = None

    document_storage_dir: str = "./storage/documents"
    max_document_size_mb: int = 20

    # AI/RAG foundation.  Disabled by default and requires no paid provider to
    # run the application.  Live embeddings require an explicitly configured
    # provider (e.g. "openai"); "test" is a deterministic provider for tests
    # and local development only.
    rag_enabled: bool = True
    rag_embedding_provider: str = ""
    rag_embedding_model: str = ""
    rag_embedding_batch_size: int = 32
    rag_chunk_size: int = 1000
    rag_chunk_overlap: int = 150
    rag_top_k: int = 5
    rag_max_top_k: int = 20
    rag_max_query_length: int = 2000
    rag_min_relevance_score: float = 0.0
    rag_max_context_words: int = 3000
    rag_llm_provider: str = ""
    rag_llm_model: str = ""
    rag_llm_temperature: float = 0.0
    rag_openai_api_url: str = "https://api.openai.com/v1"
    rag_openai_api_key: Optional[str] = None
    rag_openai_timeout_seconds: float = 30.0

    # Browser CORS origins (comma-separated).  Development defaults cover the
    # Vite dev server on its default port and the automatic fallback (5174);
    # production deployments should set this explicitly rather than relying on
    # the wildcard.
    cors_origins: str = (
        "http://localhost:5173,http://127.0.0.1:5173,"
        "http://localhost:5174,http://127.0.0.1:5174"
    )

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    """Return a cached Settings instance.

    Caching avoids re-reading the environment on every call and guarantees a
    single source of truth for configuration.
    """
    return Settings()
