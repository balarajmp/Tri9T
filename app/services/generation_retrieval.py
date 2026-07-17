from typing import List, Optional
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.models.sql.selection import Selection, SelectionNode
from app.models.sql.document import DocumentVersion
from app.models.sql.node import LogicalNode
from app.schemas.generation_retrieval import GenerationRetrievalResponse, VersionMetadata, RetrievalTestCase
from app.services.traceability import check_traceability
from app.services.version_comparison import VersionComparisonService


async def get_generation_by_selection_id(
    selection_id: int,
    db: AsyncSession
) -> GenerationRetrievalResponse:
    """
    Retrieves LLM generation details for a selection, including:
    - Generated test cases
    - Original document version metadata
    - Current latest document version metadata
    - Staleness/Traceability status
    - Node-filtered diff summary
    """
    # 1. Fetch selection with nodes and generated test cases
    stmt = (
        select(Selection)
        .options(
            selectinload(Selection.selection_nodes).selectinload(SelectionNode.logical_node),
            selectinload(Selection.document_version),
            selectinload(Selection.generated_test_cases)
        )
        .where(Selection.id == selection_id)
    )
    res = await db.execute(stmt)
    selection = res.scalar_one_or_none()
    if not selection:
        raise HTTPException(
            status_code=404,
            detail=f"Selection with ID {selection_id} not found."
        )

    original_version = selection.document_version

    # 2. Get latest version for the same document
    stmt_latest = (
        select(DocumentVersion)
        .where(DocumentVersion.document_id == original_version.document_id)
        .order_by(DocumentVersion.version_number.desc())
        .limit(1)
    )
    res_latest = await db.execute(stmt_latest)
    current_version = res_latest.scalar_one_or_none()
    if not current_version:
        current_version = original_version

    # 3. Staleness status
    trace_res = await check_traceability(selection_id, current_version.id, db)
    staleness_status = trace_res.status

    # 4. Diff summary filtered to selection's nodes
    comp_service = VersionComparisonService()
    comp_result = await comp_service.compare_document_versions(
        db, original_version.id, current_version.id
    )

    selected_uuids = {sn.logical_node.uuid for sn in selection.selection_nodes}
    filtered_changes = [
        change for change in comp_result.get("changes", [])
        if change.get("logical_node_uuid") in selected_uuids
    ]

    diff_summary = {
        "summary": {
            "unchanged_count": sum(1 for c in filtered_changes if c.get("status") == "unchanged"),
            "modified_count": sum(1 for c in filtered_changes if c.get("status") == "modified"),
            "removed_count": sum(1 for c in filtered_changes if c.get("status") == "removed")
        },
        "changes": filtered_changes
    }

    # 5. Build and return response
    return GenerationRetrievalResponse(
        selection_id=selection.id,
        selection_name=selection.name,
        original_version=VersionMetadata.model_validate(original_version),
        current_version=VersionMetadata.model_validate(current_version),
        staleness_status=staleness_status,
        diff_summary=diff_summary,
        test_cases=[
            RetrievalTestCase.model_validate(tc) for tc in selection.generated_test_cases
        ]
    )


async def get_generations_by_node_id(
    node_id_str: str,
    db: AsyncSession
) -> List[GenerationRetrievalResponse]:
    """
    Retrieves generations containing the specified node (by integer ID or UUID string).
    Returns a list of retrieval responses.
    """
    # 1. Resolve logical node
    if node_id_str.isdigit():
        stmt_ln = select(LogicalNode).where(LogicalNode.id == int(node_id_str))
    else:
        stmt_ln = select(LogicalNode).where(LogicalNode.uuid == node_id_str)

    res_ln = await db.execute(stmt_ln)
    logical_node = res_ln.scalar_one_or_none()
    if not logical_node:
        raise HTTPException(
            status_code=404,
            detail=f"Logical node '{node_id_str}' not found."
        )

    # 2. Find all selections containing this logical node
    stmt_sel = (
        select(SelectionNode.selection_id)
        .where(SelectionNode.logical_node_id == logical_node.id)
    )
    res_sel = await db.execute(stmt_sel)
    selection_ids = res_sel.scalars().all()

    # 3. Retrieve details for each selection
    responses = []
    for sel_id in selection_ids:
        try:
            resp = await get_generation_by_selection_id(sel_id, db)
            responses.append(resp)
        except HTTPException:
            continue

    return responses
