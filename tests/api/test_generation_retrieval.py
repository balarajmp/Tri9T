import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.sql.document import Document, DocumentVersion
from app.models.sql.node import LogicalNode, NodeVersion
from app.models.sql.selection import Selection, SelectionNode
from app.models.sql.generated_test_case import GeneratedTestCase


@pytest.mark.asyncio
async def test_generation_retrieval_flow(client: AsyncClient, db_session: AsyncSession):
    # 1. Seed document
    doc = Document(name="Manual X")
    db_session.add(doc)
    await db_session.flush()

    # 2. Seed V1
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
        title="Intro",
        content="Intro text.",
        content_hash="hash-1",
        sort_order=0
    )
    db_session.add(nv_a)
    await db_session.flush()

    # 3. Create selection
    sel = Selection(name="test_selection", document_version_id=v1.id)
    db_session.add(sel)
    await db_session.flush()

    sn = SelectionNode(selection_id=sel.id, logical_node_id=node_a.id, selected_text="Intro text")
    db_session.add(sn)
    await db_session.flush()

    # 4. Create generated test case
    gtc = GeneratedTestCase(
        selection_id=sel.id,
        question="What is the introduction?",
        answer="Intro text.",
        reference_context="Intro text."
    )
    db_session.add(gtc)
    await db_session.flush()

    # 5. Seed V2 with modified content
    v2 = DocumentVersion(document_id=doc.id, version_number=2, commit_message="V2 update")
    db_session.add(v2)
    await db_session.flush()

    nv_a2 = NodeVersion(
        logical_node_id=node_a.id,
        document_version_id=v2.id,
        parent_logical_node_id=None,
        title="Intro",
        content="Intro text modified.",
        content_hash="hash-2", # changed hash
        sort_order=0
    )
    db_session.add(nv_a2)
    await db_session.flush()
    await db_session.commit()

    # 6. Test GET /api/v1/generation/{selection_id}
    resp = await client.get(f"/api/v1/generation/{sel.id}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["selection_id"] == sel.id
    assert data["selection_name"] == "test_selection"
    assert data["staleness_status"] == "Possibly stale"
    assert len(data["test_cases"]) == 1
    assert data["test_cases"][0]["question"] == "What is the introduction?"
    assert data["original_version"]["version_number"] == 1
    assert data["current_version"]["version_number"] == 2
    assert "diff_summary" in data
    assert data["diff_summary"]["summary"]["modified_count"] == 1

    # 7. Test GET /api/v1/generation/node/{node_id} (using UUID)
    resp_node = await client.get(f"/api/v1/generation/node/{node_a.uuid}")
    assert resp_node.status_code == 200
    list_data = resp_node.json()
    assert len(list_data) == 1
    assert list_data[0]["selection_id"] == sel.id
    assert list_data[0]["staleness_status"] == "Possibly stale"

    # 8. Test GET /api/v1/generation/node/{node_id} (using integer ID)
    resp_node_int = await client.get(f"/api/v1/generation/node/{node_a.id}")
    assert resp_node_int.status_code == 200
    list_data_int = resp_node_int.json()
    assert len(list_data_int) == 1
