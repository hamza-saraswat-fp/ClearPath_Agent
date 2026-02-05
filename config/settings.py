"""Configuration settings for ClearPath Agent."""

from functools import lru_cache
from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Anthropic API
    anthropic_api_key: str = Field(
        ...,
        description="Anthropic API key for Claude",
    )
    anthropic_model: str = Field(
        default="claude-sonnet-4-20250514",
        description="Claude model to use",
    )

    # Supabase (Vector Store)
    supabase_url: str = Field(
        ...,
        description="Supabase project URL",
    )
    supabase_key: str = Field(
        ...,
        description="Supabase API key (service role key recommended)",
    )

    # Neo4j (Graph Store)
    neo4j_uri: Optional[str] = Field(
        default=None,
        description="Neo4j connection URI",
    )
    neo4j_username: str = Field(
        default="neo4j",
        description="Neo4j username",
    )
    neo4j_password: Optional[str] = Field(
        default=None,
        description="Neo4j password",
    )

    # OpenAI (Embeddings)
    openai_api_key: Optional[str] = Field(
        default=None,
        description="OpenAI API key for embeddings",
    )

    # Application settings
    debug: bool = Field(
        default=False,
        description="Enable debug mode",
    )
    log_level: str = Field(
        default="INFO",
        description="Logging level",
    )

    # Output settings
    output_dir: str = Field(
        default="./output",
        description="Directory for generated Excel files",
    )

    # Ingestion settings
    skip_vector_store: bool = Field(
        default=False,
        description="Skip vector store operations",
    )
    skip_graph_store: bool = Field(
        default=False,
        description="Skip graph store operations",
    )
    dry_run: bool = Field(
        default=False,
        description="Run without writing to databases",
    )

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
