"""
Living Ledger Auditor - Configuration
"""
from pydantic_settings import BaseSettings
from typing import Optional
import os


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # Application
    APP_NAME: str = "Living Ledger Auditor"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = True
    
    # API
    API_PREFIX: str = "/api"
    CORS_ORIGINS: list[str] = ["http://localhost:3000", "http://127.0.0.1:3000"]
    
    # Database (optional for demo - can run in-memory)
    DATABASE_URL: Optional[str] = None
    
    # Gemini API (Google AI Studio)
    # Get key from: https://aistudio.google.com/apikey
    GEMINI_API_KEY: Optional[str] = "AIzaSyAixuvAQBlmhNRRwHn6K7rBMSxchQyqvOs"
    GEMINI_MODEL: str = "gemini-3-flash-preview"  # Gemini 3 Flash Preview
    
    # Rate limiting
    GEMINI_REQUESTS_PER_MINUTE: int = 15
    GEMINI_MAX_RETRIES: int = 3
    
    # ===== EXTERNAL API KEYS FOR OWNERSHIP DISCOVERY =====
    # The app works without these but ownership discovery is more limited
    
    # OpenCorporates API (PAID - not using)
    # Note: OpenCorporates requires paid subscription for API access
    OPENCORPORATES_API_KEY: Optional[str] = None
    
    # UK Companies House API (FREE - configured)
    # Get key from: https://developer.company-information.service.gov.uk/
    UK_COMPANIES_HOUSE_API_KEY: Optional[str] = "1006aff0-d391-4a21-9fb0-8d4ceaa6911b"
    
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


settings = Settings()
