from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.database import engine, Base
from app.routers import auth,gateway
from app.gateway.middleware import AuthMiddleware


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager for startup and shutdown events.
    """
    # Startup: Create database tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    yield
    
    # Shutdown: Clean up resources
    await engine.dispose()


# Create FastAPI application
app = FastAPI(
    title="c2-Auth API",
    description="FastAPI backend with JWT authentication and RBAC",
    version="1.0.0",
    lifespan=lifespan
)
app.add_middleware(AuthMiddleware)
# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(auth.router)

@app.get("/", tags=["Health"])
async def root():
    """Health check endpoint."""
    return {
        "message": "c2-Auth API is running",
        "status": "healthy",
        "version": "1.0.0"
    }


@app.get("/health", tags=["Health"])
async def health_check():
    """Detailed health check endpoint."""
    return {
        "status": "healthy",
        "database": "connected"
    }

# Gateway catch-all should be registered last
app.include_router(gateway.router, tags=["Gateway"])
