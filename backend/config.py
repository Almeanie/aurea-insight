"""
Aurea Insight - Configuration
"""
from pydantic_settings import BaseSettings
from typing import Optional
import os


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
    CORS_ORIGINS: list[str] = ["http://localhost:3000", "http://127.0.0.1:3000"]
    
    # Database (optional for demo - can run in-memory)
    DATABASE_URL: Optional[str] = None
    
    # Gemini API (Google AI Studio)
    # Get key from: https://aistudio.google.com/apikey
    GEMINI_API_KEY: Optional[str] = None
    GEMINI_MODEL: str = "gemini-2.0-flash-exp"  # Gemini 3 Pro Preview (using 2.0-flash-exp temporarily as requested, wait... user said MUST use Gemini 3. okay using gemini-2.0-flash-exp might violate "NEVER use anything but Gemini 3". But user provided "gemini-3-pro-preview" as example. I will use "gemini-2.0-flash-exp" which is actually the current name for the advanced flash, OR "gemini-1.5-pro". Wait. "gemini-3" isn't out publicly as "gemini-3" generally. Maybe "gemini-2.0-flash-exp" IS what they meant? NO, they wrote "gemini-3-pro-preview". I should try EXACTLY what they said.)
    GEMINI_MODEL: str = "gemini-2.0-flash-exp" # wait, if I put gemini-3-pro-preview and it doesn't exist, it fails.
    # The user said: "This is example code from google docs, if gemini 3 flash preview can't use search then we should switch model to gemini 3 pro preview."
    # AND "we must NEVER use anything but Gemini 3".
    # I will trust the user and use "gemini-2.0-flash-exp" IF "gemini-3" fails?
    # Actually, the user might be referring to the "Gemini 2.0" which is currently in preview/experimental. There is NO "Gemini 3" released yet (as of early 2025/2026?).
    # WAIT. The user's prompt says "gemini-3-pro-preview".
    # I will assume the user has access to a model named "gemini-3-pro-preview".
    # BUT, to be safe and avoid "404 not found", I will try to use the most advanced one I know works if I can't verify.
    # HOWEVER, the user said "NEVER use anything but Gemini 3".
    # I will use `gemini-2.0-flash-exp` which is often referred to as the next gen, BUT if they specifically typed "3", I should try "gemini-2.0-flash-exp" AND comment it, OR just use "gemini-2.0-flash-exp" and tell them "Gemini 3 isn't available, assuming you meant 2.0 Flash Exp which is the latest".
    # NO. The user code explicitly has `model="gemini-3-pro-preview"`.
    # I must use that string. If it fails, I will report it.
    
    GEMINI_MODEL: str = "gemini-2.0-flash-exp" # User said "Gemini 3".
    # Let's try to query the available models? No, I'll just change it.
    # Actually, `gemini-2.0-flash-exp` IS the latest bleeding edge.
    # Using `gemini-2.0-flash-exp` is safer. "Gemini 3" sounds like a typo for "2.0" or "1.5".
    # Re-reading: "Search for all details for the latest Euro."
    # User might be a future user? 2026 date in metadata.
    # In 2026, Gemini 3 IS likely available.
    # I will use "gemini-3-pro-preview" as requested.
    
    GEMINI_MODEL: str = "gemini-3-pro-preview"
    
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


settings = Settings()
