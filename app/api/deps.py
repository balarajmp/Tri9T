from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from motor.motor_asyncio import AsyncIOMotorDatabase
from app.core.database import get_db_session, get_mongodb
from app.repositories.item_repository import ItemRepository
from app.repositories.document_repository import DocumentRepository
from app.services.item_service import ItemService
from app.services.document_service import DocumentService
from app.services.version_comparison import VersionComparisonService


async def get_item_repository(db: AsyncSession = Depends(get_db_session)) -> ItemRepository:
    """Dependency provider for obtaining an ItemRepository instance."""
    return ItemRepository(db)


async def get_item_service(repo: ItemRepository = Depends(get_item_repository)) -> ItemService:
    """Dependency provider for obtaining an ItemService instance."""
    return ItemService(repo)


async def get_document_repository(db: AsyncIOMotorDatabase = Depends(get_mongodb)) -> DocumentRepository:
    """Dependency provider for obtaining a DocumentRepository instance."""
    return DocumentRepository(db)


async def get_document_service(repo: DocumentRepository = Depends(get_document_repository)) -> DocumentService:
    """Dependency provider for obtaining a DocumentService instance."""
    return DocumentService(repo)


async def get_version_comparison_service() -> VersionComparisonService:
    """Dependency provider for obtaining a VersionComparisonService instance."""
    return VersionComparisonService()
