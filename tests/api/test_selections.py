import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.sql.document import Document, DocumentVersion
from app.models.sql.node import LogicalNode, NodeVersion


@pytest.mark.asyncio
async def test_selection_lifecycle_and_immutability(client: AsyncClient, db_session: AsyncSession):
    """
    Tests selection creation, retrieval, validation error cases, and immutability.
    Verifies that even after a new document version modifies node content, the original
    selection still points to the old version's node content.
    """
    # 1. Seed database with a document and initial version (V1)
    doc = Document(name="CT-200 User Guide")
    db_session.add(doc)
    await db_session.flush()

    v1 = DocumentVersion(document_id=doc.id, version_number=1, commit_message="Initial Release")
    db_session.add(v1)
    await db_session.flush()

    # 2. Add LogicalNodes and their V1 NodeVersions
    node_1 = LogicalNode(uuid="uuid-node-a", document_id=doc.id)
    node_2 = LogicalNode(uuid="uuid-node-b", document_id=doc.id)
    db_session.add_all([node_1, node_2])
    await db_session.flush()

    nv1_a = NodeVersion(
        logical_node_id=node_1.id,
        document_version_id=v1.id,
        parent_logical_node_id=None,
        title="1. Introduction",
        content="This is the introduction text.",
        content_hash="hash-intro-v1",
        sort_order=0
    )
    nv1_b = NodeVersion(
        logical_node_id=node_2.id,
        document_version_id=v1.id,
        parent_logical_node_id=None,
        title="2. Safety Guidelines",
        content="This is the safety text.",
        content_hash="hash-safety-v1",
        sort_order=1
    )
    db_session.add_all([nv1_a, nv1_b])
    await db_session.commit()

    # 3. Create a selection pinned to version 1
    selection_payload = {
        "name": "Safety Review Selection",
        "document_version_id": v1.id,
        "nodes": [
            {"node_id": "uuid-node-a", "selected_text": "introduction text"},
            {"node_id": str(node_2.id), "selected_text": "safety text"}
        ]
    }
    
    post_response = await client.post("/api/v1/selection", json=selection_payload)
    assert post_response.status_code == 201
    created_selection = post_response.json()
    assert created_selection["name"] == "Safety Review Selection"
    assert created_selection["document_version_id"] == v1.id
    assert created_selection["version_number"] == 1
    assert created_selection["document_name"] == "CT-200 User Guide"
    assert len(created_selection["nodes"]) == 2

    # Verify nodes details in the response
    node_a_resp = next(n for n in created_selection["nodes"] if n["logical_node_uuid"] == "uuid-node-a")
    assert node_a_resp["title"] == "1. Introduction"
    assert node_a_resp["content"] == "This is the introduction text."
    assert node_a_resp["selected_text"] == "introduction text"

    selection_id = created_selection["id"]

    # 4. Retrieve the selection using GET /selection/{id}
    get_response = await client.get(f"/api/v1/selection/{selection_id}")
    assert get_response.status_code == 200
    retrieved_selection = get_response.json()
    assert retrieved_selection["id"] == selection_id
    assert retrieved_selection["name"] == "Safety Review Selection"
    assert len(retrieved_selection["nodes"]) == 2

    # 5. Verify validation: nodes must exist in the specified document version
    # Let's create another document & node that is not part of this document version
    other_doc = Document(name="Unrelated Doc")
    db_session.add(other_doc)
    await db_session.flush()

    other_node = LogicalNode(uuid="uuid-unrelated", document_id=other_doc.id)
    db_session.add(other_node)
    await db_session.commit()

    invalid_payload = {
        "name": "Invalid Selection",
        "document_version_id": v1.id,
        "nodes": [
            {"node_id": "uuid-unrelated"}
        ]
    }
    bad_response = await client.post("/api/v1/selection", json=invalid_payload)
    assert bad_response.status_code == 400
    assert "does not exist in version 1" in bad_response.json()["detail"]

    # 6. Verify selection immutability after document re-ingestion
    # Create DocumentVersion 2 (re-ingestion)
    v2 = DocumentVersion(document_id=doc.id, version_number=2, commit_message="Update doc content")
    db_session.add(v2)
    await db_session.flush()

    # Create new NodeVersion for node_1 under V2 with modified title and content
    nv2_a = NodeVersion(
        logical_node_id=node_1.id,
        document_version_id=v2.id,
        parent_logical_node_id=None,
        title="1. Introduction (Revised)",
        content="This is the new revised introduction text.",
        content_hash="hash-intro-v2",
        sort_order=0
    )
    db_session.add(nv2_a)
    await db_session.commit()

    # Now fetch the original selection (pinned to V1)
    fetch_again_resp = await client.get(f"/api/v1/selection/{selection_id}")
    assert fetch_again_resp.status_code == 200
    selection_after_reingest = fetch_again_resp.json()

    # Verify selection details are completely unchanged (immutable)
    node_a_after = next(n for n in selection_after_reingest["nodes"] if n["logical_node_uuid"] == "uuid-node-a")
    # Title and content MUST reflect V1 state, not V2 state
    assert node_a_after["title"] == "1. Introduction"
    assert node_a_after["content"] == "This is the introduction text."
    assert node_a_after["selected_text"] == "introduction text"
