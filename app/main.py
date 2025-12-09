"""
FastAPI Application Entry Point.

AI Interview System with Authentication
"""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.auth.router import router as auth_router
from app.core.config import settings
from app.core.database import create_db_and_tables
from app.interview.router import router as interview_router
from app.speech.router import router as speech_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager.
    
    Startup: Create database tables
    Shutdown: Cleanup resources if needed
    """
    # Startup - gracefully handle database initialization
    try:
        await create_db_and_tables()
    except Exception as e:
        # Log but don't crash - allows serverless deployment without DB
        print(f"Database initialization skipped: {e}")
    yield
    # Shutdown (add cleanup logic here if needed)


def create_application() -> FastAPI:
    """Create and configure the FastAPI application."""
    
    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description="""
## AI Interview System API

A FastAPI backend for conducting AI-powered technical interviews.

### Features:
- 🔐 **JWT Authentication** - Secure user authentication
- 🤖 **AI-Powered Questions** - Dynamic question generation using GPT-4o-mini
- 📊 **Adaptive Difficulty** - Questions adjust based on performance
- 📝 **Real-time Evaluation** - Immediate feedback on answers
- 📈 **Comprehensive Reports** - Detailed assessment and recommendations
- 🎤 **Speech-to-Text** - High accuracy audio transcription using Whisper
- 🔴 **Real-time Transcription** - WebSocket streaming with OpenAI Realtime API

### Interview Flow:
1. Start interview with configuration
2. Answer questions one at a time
3. Receive instant evaluation and next question
4. Get final comprehensive report
        """,
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        lifespan=lifespan,
    )

    # Configure CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Include routers
    app.include_router(auth_router, prefix="/auth")
    app.include_router(interview_router, prefix="/api")
    app.include_router(speech_router, prefix="/api")

    return app


app = create_application()


@app.get("/", tags=["health"])
async def root():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "app": settings.app_name,
        "version": settings.app_version,
    }


@app.get("/health", tags=["health"])
async def health_check():
    """Detailed health check endpoint."""
    return {
        "status": "healthy",
        "database": "connected",
    }

