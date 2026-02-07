"""
Aurea Insight - Configuration
"""
from pydantic_settings import BaseSettings
from pydantic import computed_field
from typing import Optional
import os
import json


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # Application
    APP_NAME: str = "Aurea Insight"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = True
    LOG_LEVEL: str = "INFO"
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    
    # API
    API_PREFIX: str = "/api"
    # Raw CORS_ORIGINS as string (comma-separated or JSON array)
    CORS_ORIGINS: str = "http://localhost:3000,http://127.0.0.1:3000,https://aurea-insight-frontend-c3yaaaxyza-uc.a.run.app"
    
    @computed_field
    @property
    def cors_origins_list(self) -> list[str]:
        """Parse CORS_ORIGINS from various formats (JSON array or comma-separated)."""
        v = self.CORS_ORIGINS
        if not v:
            return ["http://localhost:3000", "http://127.0.0.1:3000"]
        # Try JSON first
        try:
            parsed = json.loads(v)
            if isinstance(parsed, list):
                return parsed
        except json.JSONDecodeError:
            pass
        # Fall back to comma-separated
        return [origin.strip() for origin in v.split(",") if origin.strip()]
    
    # Database (optional for demo - can run in-memory)
    DATABASE_URL: Optional[str] = None
    
    # Gemini API (Google AI Studio)
    # Get key from: https://aistudio.google.com/apikey
    GEMINI_API_KEY: Optional[str] = None
    
    # Model Configuration
    
    # Default model for reasoning/generation/web search
    GEMINI_MODEL: str = "gemini-3-flash-preview" 
    
    # Model for Web Search (Search Grounding)
    GEMINI_SEARCH_MODEL: str = "gemini-3-flash-preview" 
    
    # Rate limiting
    GEMINI_REQUESTS_PER_MINUTE: int = 60
    GEMINI_MAX_RETRIES: int = 3
    
    # ===== EXTERNAL API KEYS FOR OWNERSHIP DISCOVERY =====
    # The app works without these but ownership discovery is more limited
    

    
    
    # SEC EDGAR API (FREE - no key required)
    # Works automatically for US public companies
    # API docs: https://www.sec.gov/edgar/sec-api-documentation
    
    # GLEIF API (FREE - no key required)
    # Works automatically for LEI lookups (Legal Entity Identifiers)
    # API docs: https://www.gleif.org/en/lei-data/gleif-api
    GLEIF_API_ENABLED: bool = True
    
    # File Storage
    UPLOAD_DIR: str = "./uploads"
    MAX_UPLOAD_SIZE_MB: int = 50
    
    # Audit Trail
    AUDIT_TRAIL_ENABLED: bool = True
    
    class Config:
        env_file = ".env"
        case_sensitive = True
        extra = "ignore"  # Allow extra env vars that aren't defined in Settings


settings = Settings()
