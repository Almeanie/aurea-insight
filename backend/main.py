"""
Aurea Insight - Main FastAPI Application
AI-Powered Financial Audit Platform
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from loguru import logger
import sys

from config import settings
from api.routes import company, audit, ownership, chat, export, settings as settings_router


# Configure logging
logger.remove()
logger.add(
    sys.stdout,
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
    level="DEBUG" if settings.DEBUG else "INFO"
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events."""
    import asyncio
    logger.info(f"Starting {settings.APP_NAME} v{settings.APP_VERSION}")
    logger.info(f"Debug mode: {settings.DEBUG}")
    
    # Pre-initialize audit engine and Gemini client in background
    # This makes the first audit request much faster
    async def warm_up():
        try:
            from audit.engine import get_audit_engine
            logger.info("Pre-initializing audit engine...")
            engine = get_audit_engine()
            # Touch components to initialize them
            gemini = engine.gemini  # Initialize Gemini client
            _ = engine.gaap_engine  # Initialize GAAP rules
            logger.info("Audit engine pre-initialized successfully")
            
            # Send a tiny warmup call to Gemini to pre-establish the connection
            # This eliminates the cold-start delay on the first real request
            if gemini.model or gemini.client:
                logger.info("Warming up Gemini API with test call...")
                warmup_result = await gemini.generate(
                    prompt="Respond with just the word OK",
                    max_tokens=100,
                    purpose="warmup"
                )
                if warmup_result.get("text"):
                    logger.info("Gemini API warmup successful")
                else:
                    logger.warning(f"Gemini warmup returned no text: {warmup_result.get('error')}")
        except Exception as e:
            logger.warning(f"Audit engine warm-up failed (non-critical): {e}")
        
        # Pre-load SEC EDGAR tickers cache
        try:
            from ownership.registries.sec_edgar import SECEdgarAPI
            logger.info("Pre-loading SEC EDGAR tickers cache...")
            sec = SECEdgarAPI()
            await sec._load_tickers()
            logger.info("SEC EDGAR tickers cache loaded")
        except Exception as e:
            logger.warning(f"SEC EDGAR cache warm-up failed (non-critical): {e}")
    
    # Run warm-up in background (don't block startup)
    asyncio.create_task(warm_up())
    
    # Startup
    yield
    
    # Shutdown
    logger.info("Shutting down...")


# Create FastAPI app
app = FastAPI(
    title=settings.APP_NAME,
    description="AI-Powered Financial Audit Platform - Detect fraud, ensure compliance, explain everything.",
    version=settings.APP_VERSION,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(company.router, prefix=f"{settings.API_PREFIX}/companies", tags=["Companies"])
app.include_router(audit.router, prefix=f"{settings.API_PREFIX}/audit", tags=["Audit"])
app.include_router(ownership.router, prefix=f"{settings.API_PREFIX}/ownership", tags=["Ownership"])
app.include_router(chat.router, prefix=f"{settings.API_PREFIX}/chat", tags=["Chat"])
app.include_router(export.router, prefix=f"{settings.API_PREFIX}/export", tags=["Export"])
app.include_router(settings_router.router, prefix=f"{settings.API_PREFIX}/settings", tags=["Settings"])


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "status": "operational",
        "docs": "/docs"
    }


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "gemini_configured": bool(settings.GEMINI_API_KEY),
        "database_configured": bool(settings.DATABASE_URL)
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=settings.DEBUG)
