import sys
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

try:
    from .api.conversation import health_router
    from .api.conversation import router as conversation_router
    from .api.video_room import router as video_router
    from .config import settings
except ImportError:
    # For direct execution
    import os
    import sys
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from app.api.conversation import health_router
    from app.api.conversation import router as conversation_router
    from app.api.video_room import router as video_router
    from app.config import settings


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
        "slack_bot_token",
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
    Voice-enabled AI reception system for visitor management.

    Features:
    - Voice conversation using OpenAI Whisper + TTS
    - Real-time WebSocket voice streaming
    - Interactive conversation flow using LangGraph
    - Voice Activity Detection (VAD)
    - Google Calendar integration for appointment checking
    - Visitor type detection (appointment, sales, delivery)
    - Slack notifications for response logging
    - Backward compatible with text-based interface
    """,
    version="2.0.0",
    lifespan=lifespan,
    docs_url="/docs" if settings.debug else None,
    redoc_url="/redoc" if settings.debug else None
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=settings.cors_allow_credentials,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
    expose_headers=["*"]
)

# Log CORS configuration
print("🔒 CORS Configuration:")
print(f"   Environment: {settings.environment}")
print(f"   Allowed Origins: {settings.cors_origins}")
print(f"   Allow Credentials: {settings.cors_allow_credentials}")


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
app.include_router(video_router)
app.include_router(health_router)

# Add WebSocket endpoint for voice chat
from fastapi import WebSocket

from .api.websocket import handle_voice_websocket


@app.websocket("/ws/voice/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str):
    await handle_voice_websocket(websocket, session_id)


# Root endpoint
@app.get("/")
async def root():
    """Root endpoint with API information"""
    return {
        "message": "AI Reception System API",
        "version": "2.0.0",
        "environment": settings.environment,
        "features": [
            "Voice conversation (WebSocket)",
            "Text conversation (REST API)",
            "Video calls (Twilio)",
            "Real-time voice streaming",
            "Voice Activity Detection",
            "LangGraph conversation flow",
            "Google Calendar integration",
            "Slack notifications"
        ],
        "endpoints": {
            "health": "/api/health",
            "conversations": "/api/conversations",
            "video_calls": "/api/video",
            "voice_websocket": "/ws/voice/{session_id}",
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
