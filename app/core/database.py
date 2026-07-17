import logging
from collections.abc import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase
from motor.motor_asyncio import AsyncIOMotorClient
from app.core.config import settings

logger = logging.getLogger(__name__)

# --- SQLite/SQLAlchemy 2.0 Async Setup ---
# echo=True is only used in Debug mode to log SQL queries
async_engine = create_async_engine(
    settings.SQLITE_DB_URL,
    echo=settings.DEBUG,
    connect_args={"check_same_thread": False} if "sqlite" in settings.SQLITE_DB_URL else {}
)

# Async session factory
async_session_maker = async_sessionmaker(
    async_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False
)


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy database models using Declarative Mapping."""
    pass


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency for obtaining an asynchronous SQLAlchemy database session.
    Automatically commits transactions if successful, and rolls back on exception.
    """
    async with async_session_maker() as session:
        try:
            yield session
            await session.commit()
        except Exception as e:
            await session.rollback()
            logger.error(f"SQLAlchemy transaction failed, rolled back: {e}")
            raise
        finally:
            await session.close()


# --- MongoDB Motor Async Setup ---
class MongoDBManager:
    """Manages the MongoDB connection lifecycle."""
    def __init__(self) -> None:
        self.client: AsyncIOMotorClient | None = None
        self.db = None

    def connect(self) -> None:
        """Initialize MongoDB client."""
        logger.info(f"Connecting to MongoDB at {settings.MONGODB_URL}...")
        try:
            self.client = AsyncIOMotorClient(
                settings.MONGODB_URL,
                serverSelectionTimeoutMS=5000  # Fail fast if server is offline
            )
            self.db = self.client[settings.MONGODB_DB_NAME]
            logger.info("MongoDB client initialized.")
        except Exception as e:
            logger.error(f"Failed to connect to MongoDB: {e}")
            raise

    def close(self) -> None:
        """Close MongoDB client connection."""
        if self.client:
            logger.info("Closing MongoDB connection...")
            self.client.close()
            self.client = None
            self.db = None
            logger.info("MongoDB connection closed.")


# Singleton instance of the connection manager
mongodb_manager = MongoDBManager()


def get_mongodb():
    """
    Dependency for obtaining the MongoDB database instance.
    Ensures that client connection is active.
    """
    if mongodb_manager.db is None:
        raise RuntimeError("MongoDB is not initialized. Please ensure the app lifecycle is running.")
    return mongodb_manager.db
