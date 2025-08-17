import sys
import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

try:
    from .api.conversation import health_router
    from .api.conversation import router as conversation_router
    from .api.video_room import router as video_router
    from .api.health import router as health_check_router
    from .api.phase3_management import router as phase3_router
    from .config import settings
    
    # Phase 3 services
    from .services.performance_optimizer import get_performance_optimizer
    from .services.cost_optimizer import get_cost_optimizer
    from .services.monitoring_system import get_monitoring_system
    from .services.reliability_manager import get_reliability_manager, setup_default_reliability
    from .services.security_manager import get_security_manager
    
except ImportError:
    # For direct execution
    import os
    import sys
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from app.api.conversation import health_router
    from app.api.conversation import router as conversation_router
    from app.api.video_room import router as video_router
    from app.api.health import router as health_check_router
    from app.api.phase3_management import router as phase3_router
    from app.config import settings
    
    # Phase 3 services
    from app.services.performance_optimizer import get_performance_optimizer
    from app.services.cost_optimizer import get_cost_optimizer
    from app.services.monitoring_system import get_monitoring_system
    from app.services.reliability_manager import get_reliability_manager, setup_default_reliability
    from app.services.security_manager import get_security_manager


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events"""
    # Startup
    print("🚀 Reception System API starting up...")
    print(f"Environment: {settings.environment}")
    print(f"Debug mode: {settings.debug}")
    print("🔄 Phase 3: Production-Ready Optimization & Monitoring")

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
    
    # Initialize Phase 3 services
    print("🔧 Initializing Phase 3 services...")
    
    try:
        # Initialize Performance Optimizer
        performance_optimizer = await get_performance_optimizer()
        print("✅ Performance Optimizer initialized")
        
        # Initialize Cost Optimizer
        cost_optimizer = await get_cost_optimizer()
        print("✅ Cost Optimizer initialized")
        
        # Initialize Monitoring System
        monitoring_system = await get_monitoring_system()
        asyncio.create_task(monitoring_system.start_monitoring())
        print("✅ Monitoring System started")
        
        # Initialize Reliability Manager
        reliability_manager = await get_reliability_manager()
        await setup_default_reliability()
        asyncio.create_task(reliability_manager.start_reliability_monitoring())
        print("✅ Reliability Manager started")
        
        # Initialize Security Manager
        security_manager = await get_security_manager()
        print("✅ Security Manager initialized")
        
        print("🎯 Phase 3 services successfully initialized!")
        
    except Exception as e:
        print(f"❌ Phase 3 initialization error: {e}")
        if settings.environment != "development":
            sys.exit(1)
        else:
            print("🔧 Development mode: Continuing with limited functionality")

    print("✅ Reception System API started successfully")
    print("🌟 Ready for production-level operation!")

    yield

    # Shutdown
    print("🛑 Reception System API shutting down...")
    
    # Graceful shutdown of Phase 3 services
    try:
        print("🔄 Shutting down Phase 3 services...")
        
        monitoring_system = await get_monitoring_system()
        await monitoring_system.stop_monitoring()
        
        reliability_manager = await get_reliability_manager()
        await reliability_manager.stop_reliability_monitoring()
        
        performance_optimizer = await get_performance_optimizer()
        await performance_optimizer.cleanup_resources()
        
        print("✅ Phase 3 services shut down gracefully")
        
    except Exception as e:
        print(f"⚠️ Error during Phase 3 shutdown: {e}")
    
    print("👋 Goodbye!")


# Create FastAPI application
app = FastAPI(
    title="AI Reception System API - Phase 3",
    description="""
    Enterprise-grade voice-enabled AI reception system for visitor management.

    Phase 3 Features (Production-Ready):
    - Advanced performance optimization with adaptive processing
    - Real-time cost monitoring and automatic budget controls
    - Comprehensive monitoring system with alerting
    - High availability with circuit breakers and auto-recovery
    - Enhanced security with threat detection and access control
    - Production-ready deployment support

    Core Features:
    - Voice conversation using OpenAI Realtime API + Legacy modes
    - Real-time WebSocket voice streaming with optimization
    - Interactive conversation flow using LangGraph
    - Voice Activity Detection (VAD)
    - Google Calendar integration for appointment checking
    - Visitor type detection (appointment, sales, delivery)
    - Slack notifications with async delivery
    - Backward compatible with text-based interface
    """,
    version="3.0.0",
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

# Phase 3 routers
app.include_router(health_check_router)
app.include_router(phase3_router)

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
        "message": "AI Reception System API - Phase 3",
        "version": "3.0.0",
        "environment": settings.environment,
        "phase": "production-ready",
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
        "phase3_features": [
            "Performance optimization",
            "Cost monitoring & control",
            "System monitoring & alerting",
            "High availability & reliability",
            "Enhanced security",
            "Production deployment support"
        ],
        "endpoints": {
            "health": "/api/health",
            "conversations": "/api/conversations",
            "video_calls": "/api/video",
            "voice_websocket": "/ws/voice/{session_id}",
            "health_check": "/health",
            "phase3_management": "/api/v3/management",
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
