import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.sql.document import Document, DocumentVersion
from app.models.sql.node import LogicalNode, NodeVersion
from app.models.sql.selection import Selection, SelectionNode
from app.models.sql.llm_failure import LLMGenerationFailure


@pytest.mark.asyncio
async def test_llm_qa_generation_lifecycle(client: AsyncClient, db_session: AsyncSession):
    """
    Verifies LLM QA generation endpoints. Covers successful generation,
    retry-once success, and permanent failure logging.
    """
    # 1. Seed database with document, version, and logical nodes
    doc = Document(name="CT-200 Guide")
    db_session.add(doc)
    await db_session.flush()

    v1 = DocumentVersion(document_id=doc.id, version_number=1, commit_message="V1 release")
    db_session.add(v1)
    await db_session.flush()

    node_a = LogicalNode(uuid="uuid-node-a", document_id=doc.id)
    db_session.add(node_a)
    await db_session.flush()

    nv_a = NodeVersion(
        logical_node_id=node_a.id,
        document_version_id=v1.id,
        parent_logical_node_id=None,
        title="Introduction",
        content="This is the introduction text for CT-200.",
        content_hash="intro-v1",
        sort_order=0
    )
    db_session.add(nv_a)
    await db_session.flush()

    # 2. Create selections representing different scenarios
    # A) Successful scenario selection
    sel_success = Selection(name="normal_selection", document_version_id=v1.id)
    db_session.add(sel_success)
    await db_session.flush()
    sn_success = SelectionNode(selection_id=sel_success.id, logical_node_id=node_a.id, selected_text="introduction text")
    db_session.add(sn_success)

    # B) Validation failure on first attempt, success on second retry
    sel_retry = Selection(name="trigger_validation_failure", document_version_id=v1.id)
    db_session.add(sel_retry)
    await db_session.flush()
    sn_retry = SelectionNode(selection_id=sel_retry.id, logical_node_id=node_a.id)
    db_session.add(sn_retry)

    # C) Permanent validation failure (both attempts fail)
    sel_fail = Selection(name="trigger_permanent_failure", document_version_id=v1.id)
    db_session.add(sel_fail)
    await db_session.flush()
    sn_fail = SelectionNode(selection_id=sel_fail.id, logical_node_id=node_a.id)
    db_session.add(sn_fail)

    await db_session.commit()

    # 3. Test scenario A: Normal successful QA generation
    response = await client.post(f"/api/v1/selection/{sel_success.id}/qa")
    assert response.status_code == 200
    data = response.json()
    assert "test_cases" in data
    assert 3 <= len(data["test_cases"]) <= 5
    for case in data["test_cases"]:
        assert "question" in case
        assert "answer" in case
        assert "reference_context" in case

    # 4. Test scenario B: First attempt fails but retry succeeds
    response_retry = await client.post(f"/api/v1/selection/{sel_retry.id}/qa")
    assert response_retry.status_code == 200
    data_retry = response_retry.json()
    assert len(data_retry["test_cases"]) == 3

    # 5. Test scenario C: Permanent failure (both attempts fail -> store logs and return error)
    response_fail = await client.post(f"/api/v1/selection/{sel_fail.id}/qa")
    assert response_fail.status_code == 422
    data_fail = response_fail.json()
    assert "validation_error" in data_fail["detail"]
    assert "raw_response" in data_fail["detail"]

    # Verify that the failure was stored in the SQLite database
    stmt = select(LLMGenerationFailure).where(LLMGenerationFailure.selection_id == sel_fail.id)
    res = await db_session.execute(stmt)
    failure_record = res.scalar_one_or_none()
    
    assert failure_record is not None
    assert failure_record.selection_id == sel_fail.id
    assert "always fails" in failure_record.raw_response
    assert failure_record.error_message != ""
