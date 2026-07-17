from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_
from sqlalchemy.orm import selectinload
from typing import List, Optional, Any

from app.api.deps import get_db_session
from app.models.sql.document import Document, DocumentVersion
from app.models.sql.node import LogicalNode, NodeVersion
from app.schemas.versioned_document import (
    SQLDocumentResponse,
    DocumentVersionResponse,
    LogicalNodeResponse,
    NodeVersionBrief,
    NodeVersionResponse,
    SearchResultNode,
    SearchResponse,
    NodeHistoryItem,
    NodeHistoryResponse,
)

router = APIRouter()


@router.get("/documents", response_model=List[SQLDocumentResponse])
async def list_sql_documents(
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db_session)
) -> Any:
    """
    Retrieve list of versioned SQL documents with pagination.
    """
    stmt = select(Document).offset(skip).limit(limit)
    res = await db.execute(stmt)
    docs = res.scalars().all()
    return docs


@router.get("/versions", response_model=List[DocumentVersionResponse])
async def list_document_versions(
    document_id: Optional[int] = None,
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db_session)
) -> Any:
    """
    Retrieve document versions, with optional filtering by document ID.
    """
    stmt = select(DocumentVersion)
    if document_id is not None:
        stmt = stmt.where(DocumentVersion.document_id == document_id)
    stmt = stmt.offset(skip).limit(limit)
    res = await db.execute(stmt)
    versions = res.scalars().all()
    return versions


@router.get("/nodes/{id}", response_model=LogicalNodeResponse)
async def get_logical_node(
    id: str,
    db: AsyncSession = Depends(get_db_session)
) -> Any:
    """
    Retrieve details and historical versions of a logical node by its integer ID or stable UUID.
    """
    if id.isdigit():
        stmt = select(LogicalNode).where(LogicalNode.id == int(id))
    else:
        stmt = select(LogicalNode).where(LogicalNode.uuid == id)

    res = await db.execute(stmt)
    logical_node = res.scalar_one_or_none()
    if not logical_node:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Logical node with ID/UUID {id} not found"
        )

    # Fetch all node versions for this logical node
    stmt_nvs = (
        select(NodeVersion)
        .options(
            selectinload(NodeVersion.document_version),
            selectinload(NodeVersion.parent_logical_node)
        )
        .where(NodeVersion.logical_node_id == logical_node.id)
        .order_by(NodeVersion.id.asc())
    )
    res_nvs = await db.execute(stmt_nvs)
    nvs = res_nvs.scalars().all()

    node_versions_brief = []
    for nv in nvs:
        parent_uuid = nv.parent_logical_node.uuid if nv.parent_logical_node else None
        node_versions_brief.append(
            NodeVersionBrief(
                id=nv.id,
                document_version_id=nv.document_version_id,
                version_number=nv.document_version.version_number,
                parent_logical_node_uuid=parent_uuid,
                title=nv.title,
                content=nv.content,
                content_hash=nv.content_hash,
                sort_order=nv.sort_order,
            )
        )

    return LogicalNodeResponse(
        id=logical_node.id,
        uuid=logical_node.uuid,
        document_id=logical_node.document_id,
        node_versions=node_versions_brief,
    )


@router.get("/search", response_model=SearchResponse)
async def search_node_contents(
    q: str,
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db_session)
) -> Any:
    """
    Search node titles and content text across all documents and versions.
    """
    if not q:
        return SearchResponse(results=[], total_matches=0)

    # Base query for matching NodeVersions
    search_filter = or_(
        NodeVersion.content.like(f"%{q}%"),
        NodeVersion.title.like(f"%{q}%")
    )

    stmt = (
        select(NodeVersion)
        .options(
            selectinload(NodeVersion.logical_node),
            selectinload(NodeVersion.document_version).selectinload(DocumentVersion.document)
        )
        .where(search_filter)
    )

    # Get total count of matching records
    count_stmt = select(func.count(NodeVersion.id)).where(search_filter)
    total_res = await db.execute(count_stmt)
    total_matches = total_res.scalar() or 0

    # Paginate and execute
    stmt = stmt.offset(skip).limit(limit)
    res = await db.execute(stmt)
    node_versions = res.scalars().all()

    results = []
    for nv in node_versions:
        results.append(
            SearchResultNode(
                logical_node_uuid=nv.logical_node.uuid,
                document_id=nv.logical_node.document_id,
                document_name=nv.document_version.document.name,
                document_version_id=nv.document_version_id,
                version_number=nv.document_version.version_number,
                title=nv.title,
                content=nv.content,
                content_hash=nv.content_hash,
            )
        )

    return SearchResponse(results=results, total_matches=total_matches)


@router.get("/changes/{node_id}", response_model=NodeHistoryResponse)
async def get_node_change_history(
    node_id: str,
    db: AsyncSession = Depends(get_db_session)
) -> Any:
    """
    Retrieve the chronological history of changes for a specific logical node.
    Categorizes status as added, modified, or unchanged relative to its previous version.
    """
    if node_id.isdigit():
        stmt = select(LogicalNode).where(LogicalNode.id == int(node_id))
    else:
        stmt = select(LogicalNode).where(LogicalNode.uuid == node_id)

    res = await db.execute(stmt)
    logical_node = res.scalar_one_or_none()
    if not logical_node:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Logical node with ID/UUID {node_id} not found"
        )

    # Fetch all node versions in chronological order
    stmt_nvs = (
        select(NodeVersion)
        .options(
            selectinload(NodeVersion.document_version),
            selectinload(NodeVersion.parent_logical_node)
        )
        .where(NodeVersion.logical_node_id == logical_node.id)
        .order_by(NodeVersion.id.asc())
    )
    res_nvs = await db.execute(stmt_nvs)
    node_versions = res_nvs.scalars().all()

    history_items = []
    prev_hash = None

    for i, nv in enumerate(node_versions):
        status_val = "added" if i == 0 else ("unchanged" if nv.content_hash == prev_hash else "modified")
        prev_hash = nv.content_hash

        parent_uuid = nv.parent_logical_node.uuid if nv.parent_logical_node else None

        history_items.append(
            NodeHistoryItem(
                document_version_id=nv.document_version_id,
                version_number=nv.document_version.version_number,
                commit_message=nv.document_version.commit_message,
                created_at=nv.document_version.created_at,
                title=nv.title,
                content=nv.content,
                content_hash=nv.content_hash,
                parent_logical_node_uuid=parent_uuid,
                status=status_val,
            )
        )

    return NodeHistoryResponse(
        logical_node_uuid=logical_node.uuid,
        document_id=logical_node.document_id,
        history=history_items,
    )
