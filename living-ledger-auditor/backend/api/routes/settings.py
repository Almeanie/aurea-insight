"""
Settings API Routes
Handles runtime configuration updates like API keys.
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from loguru import logger

from config import settings
from core.gemini_client import GeminiClient

router = APIRouter()


class GeminiKeyUpdate(BaseModel):
    """Request model for updating Gemini API key."""
    api_key: str


class GeminiKeyResponse(BaseModel):
    """Response model for API key update."""
    success: bool
    message: str
    validated: bool = False


@router.post("/gemini-key", response_model=GeminiKeyResponse)
async def update_gemini_key(request: GeminiKeyUpdate):
    """
    Update the Gemini API key at runtime.
    Validates the key by attempting to initialize a client.
    
    Args:
        request: Contains the new API key
        
    Returns:
        Success status and validation result
    """
    logger.info("[update_gemini_key] Received request to update Gemini API key")
    
    if not request.api_key or len(request.api_key) < 10:
        raise HTTPException(status_code=400, detail="Invalid API key format")
    
    try:
        # Validate the key by creating a test client
        test_client = GeminiClient(api_key=request.api_key)
        
        if test_client.model is None and test_client.client is None:
            return GeminiKeyResponse(
                success=False,
                message="API key could not be validated. The key may be invalid.",
                validated=False
            )
        
        # Update the global settings
        settings.GEMINI_API_KEY = request.api_key
        
        logger.info("[update_gemini_key] Gemini API key updated successfully")
        
        return GeminiKeyResponse(
            success=True,
            message="API key updated successfully",
            validated=True
        )
        
    except Exception as e:
        logger.error(f"[update_gemini_key] Error validating API key: {str(e)}")
        return GeminiKeyResponse(
            success=False,
            message=f"Error validating API key: {str(e)}",
            validated=False
        )


@router.get("/gemini-status")
async def get_gemini_status():
    """
    Get the current Gemini API status.
    
    Returns:
        Current configuration status
    """
    has_key = bool(settings.GEMINI_API_KEY)
    
    return {
        "configured": has_key,
        "model": settings.GEMINI_MODEL if has_key else None,
        "requests_per_minute": settings.GEMINI_REQUESTS_PER_MINUTE,
        "max_retries": settings.GEMINI_MAX_RETRIES
    }
