from fastapi import APIRouter, Depends, HTTPException, status
from app.api.deps import get_document_service, get_version_comparison_service, get_db_session
from app.schemas.document import DocumentCreate, DocumentResponse, DocumentUpdate
from app.schemas.version_comparison import VersionComparisonResponse
from app.services.document_service import DocumentService
from app.services.version_comparison import VersionComparisonService
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Any

router = APIRouter()


@router.get("", response_model=list[DocumentResponse])
async def list_documents(
    skip: int = 0,
    limit: int = 100,
    document_service: DocumentService = Depends(get_document_service)
) -> list[DocumentResponse]:
    """Retrieve a list of document records from NoSQL database."""
    docs = await document_service.list_documents(skip=skip, limit=limit)
    return [DocumentResponse(**doc) for doc in docs]


@router.get("/{document_id}", response_model=DocumentResponse)
async def get_document(
    document_id: str,
    document_service: DocumentService = Depends(get_document_service)
) -> DocumentResponse:
    """Retrieve a document record by ID."""
    doc = await document_service.get_document(document_id)
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document record with ID {document_id} not found"
        )
    return DocumentResponse(**doc)


@router.post("", response_model=DocumentResponse, status_code=status.HTTP_201_CREATED)
async def create_document(
    doc_in: DocumentCreate,
    document_service: DocumentService = Depends(get_document_service)
) -> DocumentResponse:
    """Create a new document record."""
    doc = await document_service.create_document(doc_in)
    return DocumentResponse(**doc)


@router.put("/{document_id}", response_model=DocumentResponse)
async def update_document(
    document_id: str,
    doc_in: DocumentUpdate,
    document_service: DocumentService = Depends(get_document_service)
) -> DocumentResponse:
    """Update metadata or fields of a document record."""
    doc = await document_service.update_document(document_id, doc_in)
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document record with ID {document_id} not found"
        )
    return DocumentResponse(**doc)


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(
    document_id: str,
    document_service: DocumentService = Depends(get_document_service)
) -> None:
    """Delete a document record from the system."""
    success = await document_service.delete_document(document_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document record with ID {document_id} not found"
        )


@router.get("/versions/{v1_id}/compare/{v2_id}", response_model=VersionComparisonResponse)
async def compare_document_versions(
    v1_id: int,
    v2_id: int,
    db: AsyncSession = Depends(get_db_session),
    comparison_service: VersionComparisonService = Depends(get_version_comparison_service)
) -> Any:
    """Compare two document versions and detect unchanged, modified, added, and removed nodes."""
    res = await comparison_service.compare_document_versions(db, v1_id, v2_id)
    if "error" in res:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=res["error"]
        )
    return res
