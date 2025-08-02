from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import asyncio
import sys
from contextlib import asynccontextmanager
try:
    from .config import settings
    from .api.conversation import router as conversation_router, health_router
except ImportError:
    # For direct execution
    import sys
    import os
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from app.config import settings
    from app.api.conversation import router as conversation_router, health_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events"""
    # Startup
    print("🚀 Reception System API starting up...")
    print(f"Environment: {settings.environment}")
    print(f"Debug mode: {settings.debug}")
    
    # Validate required environment variables (with development fallbacks)
    required_vars = [
        "openai_api_key",
        "google_service_account_key", 
        "slack_webhook_url",
        "meeting_room_calendar_ids"
    ]
    
    missing_vars = []
    for var in required_vars:
        if not getattr(settings, var, None):
            missing_vars.append(var.upper())
    
    if missing_vars:
        if settings.environment == "development":
            print(f"⚠️  Missing environment variables in development mode: {', '.join(missing_vars)}")
            print("🔧 Development mode: API calls will be mocked")
        else:
            print(f"❌ Missing required environment variables: {', '.join(missing_vars)}")
            sys.exit(1)
    
    print("✅ All required environment variables are set")
    print("✅ Reception System API started successfully")
    
    yield
    
    # Shutdown
    print("🛑 Reception System API shutting down...")


# Create FastAPI application
app = FastAPI(
    title="AI Reception System API",
    description="""
    Text-based AI reception system for visitor management.
    
    Features:
    - Interactive conversation flow using LangGraph
    - Google Calendar integration for appointment checking
    - Visitor type detection (appointment, sales, delivery)
    - Slack notifications for response logging
    - Extensible architecture for Step2 voice features
    """,
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs" if settings.debug else None,
    redoc_url="/redoc" if settings.debug else None
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
    expose_headers=["*"]
)


# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Global exception handler for unhandled errors"""
    print(f"Unhandled exception: {exc}")
    
    if settings.debug:
        import traceback
        traceback.print_exc()
    
    return JSONResponse(
        status_code=500,
        content={
            "detail": "Internal server error occurred",
            "error": str(exc) if settings.debug else "Server error"
        }
    )


# Include routers
app.include_router(conversation_router)
app.include_router(health_router)


# Root endpoint
@app.get("/")
async def root():
    """Root endpoint with API information"""
    return {
        "message": "AI Reception System API",
        "version": "1.0.0",
        "environment": settings.environment,
        "endpoints": {
            "health": "/api/health",
            "conversations": "/api/conversations",
            "docs": "/docs" if settings.debug else "disabled",
            "redoc": "/redoc" if settings.debug else "disabled"
        }
    }


# Development server runner
if __name__ == "__main__":
    import uvicorn
    
    # Run with hot reload in development
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.debug,
        log_level="info" if settings.debug else "warning"
    )