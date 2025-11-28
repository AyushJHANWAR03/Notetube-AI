from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings

# Create FastAPI app
app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_PREFIX}/openapi.json",
    docs_url=f"{settings.API_V1_PREFIX}/docs",
    redoc_url=f"{settings.API_V1_PREFIX}/redoc",
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.FRONTEND_URL],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": "Welcome to NoteTube AI API",
        "version": "1.0.0",
        "docs": f"{settings.BACKEND_URL}{settings.API_V1_PREFIX}/docs"
    }


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}


# Import and include routers
from app.api.routes import auth, test_youtube, videos, user_notes

# Include auth routers (no prefix since they define their own)
app.include_router(auth.router)
app.include_router(auth.user_router)

# Include video processing routes
app.include_router(videos.router)

# Include user notes routes
app.include_router(user_notes.router)

# Include test router (for development only)
app.include_router(test_youtube.router)
