from typing import Any, Dict, List
from app.repositories.document_repository import DocumentRepository
from app.schemas.document import DocumentCreate, DocumentUpdate


class DocumentService:
    """
    Service layer orchestrating all business logic around NoSQL Document entities.
    Integrates with DocumentRepository to validate and manipulate database states.
    """
    def __init__(self, repository: DocumentRepository) -> None:
        self.repository = repository

    async def get_document(self, id: str) -> Dict[str, Any] | None:
        """Fetch a specific document."""
        return await self.repository.get(id)

    async def list_documents(self, skip: int = 0, limit: int = 100) -> List[Dict[str, Any]]:
        """List documents with pagination."""
        return await self.repository.get_all(skip=skip, limit=limit)

    async def create_document(self, obj_in: DocumentCreate) -> Dict[str, Any]:
        """Create and store a document record."""
        return await self.repository.create(obj_in)

    async def update_document(self, id: str, obj_in: DocumentUpdate) -> Dict[str, Any] | None:
        """Update an existing document record."""
        return await self.repository.update(id, obj_in)

    async def delete_document(self, id: str) -> bool:
        """Remove a document record."""
        return await self.repository.remove(id)
