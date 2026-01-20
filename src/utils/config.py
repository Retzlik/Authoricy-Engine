"""
Configuration Management

Uses Pydantic Settings for environment-based configuration.
Loads from .env file automatically.
"""

from typing import Optional
from functools import lru_cache
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment."""
    
    # DataForSEO (Required)
    DATAFORSEO_LOGIN: str
    DATAFORSEO_PASSWORD: str
    
    # Claude API (Required for analysis)
    ANTHROPIC_API_KEY: str
    CLAUDE_MODEL: str = "claude-sonnet-4-20250514"
    
    # Resend (Optional - for email delivery)
    RESEND_API_KEY: Optional[str] = None
    
    # Application Settings
    ENVIRONMENT: str = "development"
    LOG_LEVEL: str = "INFO"
    
    # Default analysis settings
    DEFAULT_MARKET: str = "Sweden"
    DEFAULT_LANGUAGE: str = "sv"
    
    # Limits
    MAX_SEED_KEYWORDS: int = 5
    MAX_COMPETITORS: int = 5
    MAX_BACKLINKS: int = 500
    
    # Timeouts
    API_TIMEOUT: int = 60
    ANALYSIS_TIMEOUT: int = 300

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"  # Ignore extra fields in .env file
        case_sensitive = False  # Allow both UPPERCASE and lowercase


@lru_cache
def get_settings() -> Settings:
    """Get or create cached settings instance."""
    return Settings()
