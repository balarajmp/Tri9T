import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import api_router
from app.core.config import settings
from app.core.database import async_engine, mongodb_manager
from app.core.logging import setup_logging

# Initialize Logging configuration
setup_logging()
logger = logging.getLogger("app.main")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None]:
    """
    Handles application startup and shutdown events.
    Initializes database pools and MongoDB connections.
    """
    logger.info("Initializing application resources...")

    # Connect to MongoDB
    mongodb_manager.connect()

    # Verify SQLite database connection
    try:
        async with async_engine.connect() as conn:
            logger.info("SQLite database connection successfully verified.")
    except Exception as e:
        logger.critical(f"Database verification failed: {e}")

    yield

    logger.info("Cleaning up application resources...")

    # Close MongoDB connections
    mongodb_manager.close()

    # Close SQLAlchemy database pools
    await async_engine.dispose()
    logger.info("Cleanup completed. Goodbye!")


app = FastAPI(
    title=settings.APP_NAME,
    description="Clean Architecture Production-Quality Backend Setup",
    version="1.0.0",
    lifespan=lifespan,
    docs_url=f"{settings.API_V1_STR}/docs" if settings.DEBUG else None,
    redoc_url=f"{settings.API_V1_STR}/redoc" if settings.DEBUG else None,
    openapi_url=f"{settings.API_V1_STR}/openapi.json" if settings.DEBUG else None,
)

# Setup CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Adjust as needed for production deployment
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routes
app.include_router(api_router, prefix=settings.API_V1_STR)
