from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from typing import Any

from app.api.deps import get_db_session
from app.models.sql.document import DocumentVersion
from app.models.sql.node import LogicalNode, NodeVersion
from app.models.sql.selection import Selection, SelectionNode
from app.schemas.selection import SelectionCreate, SelectionResponse, SelectionNodeResponse
from app.schemas.qa_generation import QAGenerationResponse

router = APIRouter()


@router.post("/selection", response_model=SelectionResponse, status_code=status.HTTP_201_CREATED)
async def create_selection(
    payload: SelectionCreate,
    db: AsyncSession = Depends(get_db_session)
) -> Any:
    """
    Create a selection pinned to a specific document version.
    Validates that each selected logical node exists within that specific document version.
    """
    # 1. Fetch and verify document version
    stmt_version = (
        select(DocumentVersion)
        .options(selectinload(DocumentVersion.document))
        .where(DocumentVersion.id == payload.document_version_id)
    )
    res_version = await db.execute(stmt_version)
    doc_version = res_version.scalar_one_or_none()
    if not doc_version:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document version {payload.document_version_id} not found."
        )

    # 2. Resolve logical nodes and verify existence in this version
    selection_nodes_to_create = []
    for item in payload.nodes:
        if item.node_id.isdigit():
            stmt_nv = (
                select(NodeVersion)
                .options(selectinload(NodeVersion.logical_node))
                .where(
                    NodeVersion.document_version_id == doc_version.id,
                    NodeVersion.logical_node_id == int(item.node_id)
                )
            )
        else:
            stmt_nv = (
                select(NodeVersion)
                .join(LogicalNode, NodeVersion.logical_node_id == LogicalNode.id)
                .options(selectinload(NodeVersion.logical_node))
                .where(
                    NodeVersion.document_version_id == doc_version.id,
                    LogicalNode.uuid == item.node_id
                )
            )

        res_nv = await db.execute(stmt_nv)
        nv = res_nv.scalar_one_or_none()
        if not nv:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Logical node '{item.node_id}' does not exist in version {doc_version.version_number}."
            )

        selection_nodes_to_create.append(
            SelectionNode(
                logical_node_id=nv.logical_node_id,
                selected_text=item.selected_text
            )
        )

    # 3. Create the parent Selection record
    selection = Selection(
        name=payload.name,
        document_version_id=doc_version.id
    )
    db.add(selection)
    await db.flush()  # Populate selection.id

    # 4. Save individual SelectionNode mappings
    for sn in selection_nodes_to_create:
        sn.selection_id = selection.id
        db.add(sn)

    await db.commit()

    # 5. Retrieve complete selection object with fully populated node details for response
    stmt_full = (
        select(Selection)
        .options(
            selectinload(Selection.document_version).selectinload(DocumentVersion.document),
            selectinload(Selection.selection_nodes).selectinload(SelectionNode.logical_node)
        )
        .where(Selection.id == selection.id)
    )
    res_full = await db.execute(stmt_full)
    full_selection = res_full.scalar_one()

    logical_node_ids = [sn.logical_node_id for sn in full_selection.selection_nodes]
    nvs_dict = {}
    if logical_node_ids:
        stmt_nvs = (
            select(NodeVersion)
            .where(
                NodeVersion.logical_node_id.in_(logical_node_ids),
                NodeVersion.document_version_id == full_selection.document_version_id
            )
        )
        res_nvs = await db.execute(stmt_nvs)
        nvs_dict = {nv.logical_node_id: nv for nv in res_nvs.scalars().all()}

    nodes_response = []
    for sn in full_selection.selection_nodes:
        nv = nvs_dict.get(sn.logical_node_id)
        nodes_response.append(
            SelectionNodeResponse(
                logical_node_uuid=sn.logical_node.uuid,
                logical_node_id=sn.logical_node_id,
                title=nv.title if nv else None,
                content=nv.content if nv else None,
                selected_text=sn.selected_text
            )
        )

    return SelectionResponse(
        id=full_selection.id,
        name=full_selection.name,
        document_version_id=full_selection.document_version_id,
        version_number=full_selection.document_version.version_number,
        document_name=full_selection.document_version.document.name,
        created_at=full_selection.created_at,
        updated_at=full_selection.updated_at,
        nodes=nodes_response
    )


@router.get("/selection/{id}", response_model=SelectionResponse)
async def get_selection(
    id: int,
    db: AsyncSession = Depends(get_db_session)
) -> Any:
    """
    Retrieve selection details by its integer ID.
    Reconstructs the selection nodes' titles and contents based on the pinned document version.
    """
    stmt = (
        select(Selection)
        .options(
            selectinload(Selection.document_version).selectinload(DocumentVersion.document),
            selectinload(Selection.selection_nodes).selectinload(SelectionNode.logical_node)
        )
        .where(Selection.id == id)
    )
    res = await db.execute(stmt)
    selection = res.scalar_one_or_none()
    if not selection:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Selection with ID {id} not found."
        )

    logical_node_ids = [sn.logical_node_id for sn in selection.selection_nodes]
    nvs_dict = {}
    if logical_node_ids:
        stmt_nvs = (
            select(NodeVersion)
            .where(
                NodeVersion.logical_node_id.in_(logical_node_ids),
                NodeVersion.document_version_id == selection.document_version_id
            )
        )
        res_nvs = await db.execute(stmt_nvs)
        nvs_dict = {nv.logical_node_id: nv for nv in res_nvs.scalars().all()}

    nodes_response = []
    for sn in selection.selection_nodes:
        nv = nvs_dict.get(sn.logical_node_id)
        nodes_response.append(
            SelectionNodeResponse(
                logical_node_uuid=sn.logical_node.uuid,
                logical_node_id=sn.logical_node_id,
                title=nv.title if nv else None,
                content=nv.content if nv else None,
                selected_text=sn.selected_text
            )
        )

    return SelectionResponse(
        id=selection.id,
        name=selection.name,
        document_version_id=selection.document_version_id,
        version_number=selection.document_version.version_number,
        document_name=selection.document_version.document.name,
        created_at=selection.created_at,
        updated_at=selection.updated_at,
        nodes=nodes_response
    )


@router.post("/selection/{id}/qa", response_model=QAGenerationResponse)
async def generate_qa_test_cases(
    id: int,
    db: AsyncSession = Depends(get_db_session)
) -> Any:
    """
    Generate 3 to 5 QA test cases from the text context of a selection.
    Uses structured output with validation, retrying on validation failures and logging errors.
    """
    from app.services.llm_generation import generate_qa_for_selection
    return await generate_qa_for_selection(selection_id=id, db=db)

