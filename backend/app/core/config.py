from functools import lru_cache
from typing import List
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import field_validator
import os

class Settings(BaseSettings):
    env_name: str = os.getenv("ENV", "development")
    model_config = SettingsConfigDict(
        env_file=str(Path(__file__).parent.parent.parent / "config" / f".env.{env_name}"),
        case_sensitive=False,
        extra="ignore",
    )

    app_name: str = "ALYPSE APP"
    app_version: str = "1.0.0"
    debug: bool = False

    # Database
    database_url: str = "postgresql://postgres:root@localhost:5432/orris1,https://orris-4vg9-mynkgupta22s-projects.vercel.app"    
    # JWT
    jwt_secret_key: str = "default-secret-key"
    jwt_refresh_secret_key: str = "default-refresh-secret-key"
    jwt_algorithm: str = "HS512"
    access_token_expire_minutes: int = 15
    refresh_token_expire_days: int = 7
    
    # OpenAI
    openai_api_key: str = ""

    # Vector DB (Qdrant)
    qdrant_host: str = "localhost"
    qdrant_port: str = "6333"
    qdrant_collection_name: str ="alypse_rag"

    # Embeddings
    nomic_api_key: str = ""
    huggingface_api_key: str = ""
    embedding_model_name: str = "BAAI/bge-m3"
    embed_batch_size: int = 8

    # Document Processing
    chunk_size: str = "1000"
    chunk_overlap: str = "200"
    temp_dir: str = "/tmp"


    # CORS
    allowed_origins:str="http://localhost:3000"

@lru_cache()
def get_settings() -> Settings:
    return Settings()


settings = get_settings()