"""
Settings and Configuration for EmailPilot Simple

Manages environment variables and system configuration.
"""

import os
from typing import Optional
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""

    # API Keys
    ANTHROPIC_API_KEY: str

    # MCP Configuration
    MCP_PORT: int = 3334
    MCP_HOST: str = "localhost"

    # Firestore
    FIRESTORE_PROJECT_ID: str

    # RAG Configuration
    RAG_BASE_PATH: str = "/Users/Damon/klaviyo/klaviyo-audit-automation/shared_modules/rag"

    # Model Configuration
    CLAUDE_MODEL: str = "claude-sonnet-4-5-20250929"
    MAX_TOKENS_PLANNING: int = 8000
    MAX_TOKENS_STRUCTURING: int = 8000
    MAX_TOKENS_BRIEFS: int = 16000

    # Cache Configuration
    CACHE_TTL_SECONDS: int = 3600  # 1 hour

    # Logging
    LOG_LEVEL: str = "INFO"
    LOG_FILE: Optional[str] = None

    # Workflow Configuration
    WORKFLOW_TIMEOUT_SECONDS: int = 300  # 5 minutes
    ENABLE_VALIDATION: bool = True

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


# Global settings instance
settings = Settings()
