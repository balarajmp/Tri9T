import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from httpx import AsyncClient

from app.models.sql.document import Document, DocumentVersion
from app.models.sql.node import LogicalNode, NodeVersion
from app.services.version_comparison import VersionComparisonService


@pytest.mark.asyncio
async def test_version_comparison_service(db_session: AsyncSession):
    """
    Unit test for the VersionComparisonService directly, verifying:
    - Accurate categorisation of unchanged, modified, added, and removed nodes.
    - Correction of heading paths by walking logical hierarchies.
    - Content hash comparisons.
    """
    # 1. Create a root Document
    doc = Document(name="Versioning Test Document")
    db_session.add(doc)
    await db_session.flush()

    # 2. Create V1 and V2 DocumentVersion records
    v1 = DocumentVersion(document_id=doc.id, version_number=1, commit_message="V1 initial import")
    v2 = DocumentVersion(document_id=doc.id, version_number=2, commit_message="V2 update")
    db_session.add_all([v1, v2])
    await db_session.flush()

    # 3. Create LogicalNodes
    p = LogicalNode(uuid="uuid-p", document_id=doc.id)  # Parent heading
    a = LogicalNode(uuid="uuid-a", document_id=doc.id)  # Unchanged node
    b = LogicalNode(uuid="uuid-b", document_id=doc.id)  # Modified node
    c = LogicalNode(uuid="uuid-c", document_id=doc.id)  # Added node
    d = LogicalNode(uuid="uuid-d", document_id=doc.id)  # Removed node
    db_session.add_all([p, a, b, c, d])
    await db_session.flush()

    # 4. Create NodeVersion associations
    # Parent Section Node
    p_v1 = NodeVersion(logical_node_id=p.id, document_version_id=v1.id, parent_logical_node_id=None, title="Section 1", content="Section 1 Title", content_hash="hash-p", sort_order=0)
    p_v2 = NodeVersion(logical_node_id=p.id, document_version_id=v2.id, parent_logical_node_id=None, title="Section 1", content="Section 1 Title", content_hash="hash-p", sort_order=0)

    # Node A (Unchanged)
    a_v1 = NodeVersion(logical_node_id=a.id, document_version_id=v1.id, parent_logical_node_id=p.id, title="Paragraph", content="A's stable content", content_hash="hash-a", sort_order=1)
    a_v2 = NodeVersion(logical_node_id=a.id, document_version_id=v2.id, parent_logical_node_id=p.id, title="Paragraph", content="A's stable content", content_hash="hash-a", sort_order=1)

    # Node B (Modified)
    b_v1 = NodeVersion(logical_node_id=b.id, document_version_id=v1.id, parent_logical_node_id=p.id, title="Paragraph", content="B's old content", content_hash="hash-b-old", sort_order=2)
    b_v2 = NodeVersion(logical_node_id=b.id, document_version_id=v2.id, parent_logical_node_id=p.id, title="Paragraph", content="B's new content", content_hash="hash-b-new", sort_order=2)

    # Node C (Added in V2)
    c_v2 = NodeVersion(logical_node_id=c.id, document_version_id=v2.id, parent_logical_node_id=p.id, title="Paragraph", content="C's added content", content_hash="hash-c", sort_order=3)

    # Node D (Removed in V2)
    d_v1 = NodeVersion(logical_node_id=d.id, document_version_id=v1.id, parent_logical_node_id=p.id, title="Paragraph", content="D's deleted content", content_hash="hash-d", sort_order=4)

    db_session.add_all([p_v1, p_v2, a_v1, a_v2, b_v1, b_v2, c_v2, d_v1])
    await db_session.commit()

    # 5. Run the comparison service
    service = VersionComparisonService()
    comparison = await service.compare_document_versions(db_session, v1.id, v2.id)

    assert "error" not in comparison
    assert comparison["v1_version_number"] == 1
    assert comparison["v2_version_number"] == 2
    
    summary = comparison["summary"]
    assert summary["unchanged_count"] == 2  # Section 1 + Node A
    assert summary["modified_count"] == 1   # Node B
    assert summary["added_count"] == 1      # Node C
    assert summary["removed_count"] == 1    # Node D

    changes = {c["logical_node_uuid"]: c for c in comparison["changes"]}

    # Assert Unchanged Node (Node A)
    assert changes["uuid-a"]["status"] == "unchanged"
    assert changes["uuid-a"]["v1_path"] == "Section 1"
    assert changes["uuid-a"]["v2_path"] == "Section 1"
    assert changes["uuid-a"]["is_moved"] is False

    # Assert Modified Node (Node B)
    assert changes["uuid-b"]["status"] == "modified"
    assert changes["uuid-b"]["v1_content"] == "B's old content"
    assert changes["uuid-b"]["v2_content"] == "B's new content"

    # Assert Added Node (Node C)
    assert changes["uuid-c"]["status"] == "added"
    assert changes["uuid-c"]["v1_path"] is None
    assert changes["uuid-c"]["v2_path"] == "Section 1"
    assert changes["uuid-c"]["v2_content"] == "C's added content"

    # Assert Removed Node (Node D)
    assert changes["uuid-d"]["status"] == "removed"
    assert changes["uuid-d"]["v1_path"] == "Section 1"
    assert changes["uuid-d"]["v2_path"] is None
    assert changes["uuid-d"]["v1_content"] == "D's deleted content"


@pytest.mark.asyncio
async def test_version_comparison_api(client: AsyncClient, db_session: AsyncSession):
    """
    Tests the GET /api/v1/documents/versions/{v1_id}/compare/{v2_id} API endpoint.
    """
    # 1. Create a root Document and version IDs
    doc = Document(name="API Versioning Test")
    db_session.add(doc)
    await db_session.flush()

    v1 = DocumentVersion(document_id=doc.id, version_number=1, commit_message="V1")
    v2 = DocumentVersion(document_id=doc.id, version_number=2, commit_message="V2")
    db_session.add_all([v1, v2])
    await db_session.flush()

    # Create one modified logical node to test API response structure
    node = LogicalNode(uuid="uuid-api-node", document_id=doc.id)
    db_session.add(node)
    await db_session.flush()

    nv1 = NodeVersion(logical_node_id=node.id, document_version_id=v1.id, parent_logical_node_id=None, title="Paragraph", content="Old Content", content_hash="hash-1", sort_order=0)
    nv2 = NodeVersion(logical_node_id=node.id, document_version_id=v2.id, parent_logical_node_id=None, title="Paragraph", content="New Content", content_hash="hash-2", sort_order=0)
    db_session.add_all([nv1, nv2])
    await db_session.commit()

    # 2. Call the FastAPI endpoint
    response = await client.get(f"/api/v1/documents/versions/{v1.id}/compare/{v2.id}")
    assert response.status_code == 200

    data = response.json()
    assert data["v1_version_number"] == 1
    assert data["v2_version_number"] == 2
    assert data["summary"]["modified_count"] == 1
    assert len(data["changes"]) == 1
    
    change = data["changes"][0]
    assert change["logical_node_uuid"] == "uuid-api-node"
    assert change["status"] == "modified"
    assert change["v1_content"] == "Old Content"
    assert change["v2_content"] == "New Content"


@pytest.mark.asyncio
async def test_version_comparison_not_found(client: AsyncClient):
    """
    Tests error handling when requesting non-existent version IDs.
    """
    response = await client.get("/api/v1/documents/versions/9999/compare/8888")
    assert response.status_code == 404
    assert "not found" in response.json()["detail"]
