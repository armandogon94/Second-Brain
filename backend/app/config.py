from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Database
    database_url: str = (
        "postgresql+asyncpg://armando:changeme@localhost:5432/second_brain_db"
    )

    # API Keys
    openai_api_key: str = ""
    anthropic_api_key: str = ""

    # Telegram
    telegram_bot_token: str = ""
    telegram_user_id: int = 0
    webhook_url: str = ""
    webhook_secret: str = ""

    # Application
    environment: str = "development"
    secret_key: str = "dev-secret-key-change-in-production"
    log_level: str = "INFO"

    # Embedding
    embedding_model: str = "text-embedding-3-small"
    embedding_dimensions: int = 1536

    # LLM
    default_llm_model: str = "haiku"

    # Chunking
    chunk_size: int = 500
    chunk_overlap: int = 50
    min_chunk_size: int = 100

    # Search
    search_limit: int = 10
    rrf_k: int = 60
    similarity_threshold: float = 0.3

    # Uploads
    upload_dir: str = "uploads"
    max_file_size: int = 50 * 1024 * 1024  # 50 MB

    model_config = {"env_file": ".env", "extra": "ignore"}


settings = Settings()
