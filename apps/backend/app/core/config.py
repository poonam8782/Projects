from functools import lru_cache
from typing import Any, List, Optional, Union

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import field_validator


class Settings(BaseSettings):
    app_name: str = "Neura"
    supabase_url: Optional[str] = Field(default=None, alias="SUPABASE_URL")
    supabase_service_role_key: Optional[str] = Field(default=None, alias="SUPABASE_SERVICE_ROLE_KEY")
    supabase_anon_key: Optional[str] = Field(default=None, alias="SUPABASE_ANON_KEY")
    gemini_api_key: Optional[str] = Field(default=None, alias="GEMINI_API_KEY")
    # Preferred chat/generation model (defaults to longest-context stable model)
    gemini_chat_model: str = Field(default="gemini-2.5-pro", alias="GEMINI_CHAT_MODEL")
    # Global default cap for model output tokens; endpoints can override
    gemini_max_output_tokens: int = Field(default=8192, alias="GEMINI_MAX_OUTPUT_TOKENS")
    # Embedding model and dimensionality
    gemini_embedding_model: str = Field(default="models/embedding-001", alias="GEMINI_EMBEDDING_MODEL")
    gemini_embedding_dimensions: int = Field(default=768, alias="GEMINI_EMBEDDING_DIMENSIONS")
    # Flag to indicate if using a paid Gemini key to relax rate limits/delays
    gemini_paid: bool = Field(default=False, alias="GEMINI_PAID")
    cors_origins: Union[List[str], str] = Field(default="http://localhost:3000")
    backend_url: str = Field(default="http://localhost:8000", alias="BACKEND_URL")

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    @field_validator("cors_origins", mode="before")
    @classmethod
    def split_cors_origins(cls, value: Any) -> List[str]:
        if isinstance(value, str):
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        return value


@lru_cache()
def get_settings() -> Settings:
    return Settings()