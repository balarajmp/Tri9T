import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.sql.document import Document, DocumentVersion
from app.models.sql.node import LogicalNode, NodeVersion


@pytest.mark.asyncio
async def test_versioned_docs_apis(client: AsyncClient, db_session: AsyncSession):
    """
    Tests the versioned document browsing, version querying, node retrieval,
    searching, and change history REST endpoints.
    """
    # 1. Seed database with a test Document
    doc = Document(name="REST API Test Doc")
    db_session.add(doc)
    await db_session.flush()

    # 2. Add two DocumentVersions
    v1 = DocumentVersion(document_id=doc.id, version_number=1, commit_message="First version")
    v2 = DocumentVersion(document_id=doc.id, version_number=2, commit_message="Second version")
    db_session.add_all([v1, v2])
    await db_session.flush()

    # 3. Add LogicalNodes
    node_1 = LogicalNode(uuid="uuid-node-1", document_id=doc.id)
    node_2 = LogicalNode(uuid="uuid-node-2", document_id=doc.id)
    db_session.add_all([node_1, node_2])
    await db_session.flush()

    # 4. Add NodeVersions
    # Node 1 is present in both versions and changes content (modified)
    nv1_1 = NodeVersion(logical_node_id=node_1.id, document_version_id=v1.id, parent_logical_node_id=None, title="Heading 1", content="This is content of node 1", content_hash="hash-1", sort_order=0)
    nv1_2 = NodeVersion(logical_node_id=node_1.id, document_version_id=v2.id, parent_logical_node_id=None, title="Heading 1", content="Modified content of node 1", content_hash="hash-1-mod", sort_order=0)
    
    # Node 2 is present only in V1 (removed in V2)
    nv2_1 = NodeVersion(logical_node_id=node_2.id, document_version_id=v1.id, parent_logical_node_id=None, title="Heading 2", content="Content of node 2", content_hash="hash-2", sort_order=1)
    
    db_session.add_all([nv1_1, nv1_2, nv2_1])
    await db_session.commit()

    # 5. Verify GET /documents (SQL listing)
    response = await client.get("/api/v1/documents")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["name"] == "REST API Test Doc"

    # 6. Verify GET /versions
    response = await client.get(f"/api/v1/versions?document_id={doc.id}")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    assert data[0]["version_number"] == 1
    assert data[1]["version_number"] == 2

    # 7. Verify GET /nodes/{id} (by stable UUID)
    response = await client.get("/api/v1/nodes/uuid-node-1")
    assert response.status_code == 200
    data = response.json()
    assert data["uuid"] == "uuid-node-1"
    assert len(data["node_versions"]) == 2
    assert data["node_versions"][0]["content"] == "This is content of node 1"
    assert data["node_versions"][1]["content"] == "Modified content of node 1"

    # Verify GET /nodes/{id} (by integer ID)
    response = await client.get(f"/api/v1/nodes/{node_1.id}")
    assert response.status_code == 200
    assert response.json()["uuid"] == "uuid-node-1"

    # Verify GET /nodes/{id} returns 404 for invalid node
    response = await client.get("/api/v1/nodes/non-existent-uuid")
    assert response.status_code == 404

    # 8. Verify GET /search (by text keyword)
    response = await client.get("/api/v1/search?q=content")
    assert response.status_code == 200
    data = response.json()
    assert data["total_matches"] == 3  # Matches nv1_1, nv1_2, and nv2_1
    assert len(data["results"]) == 3
    titles = [res["title"] for res in data["results"]]
    assert "Heading 1" in titles
    assert "Heading 2" in titles

    # 9. Verify GET /changes/{node_id} (history trace)
    response = await client.get("/api/v1/changes/uuid-node-1")
    assert response.status_code == 200
    data = response.json()
    assert data["logical_node_uuid"] == "uuid-node-1"
    assert len(data["history"]) == 2
    assert data["history"][0]["status"] == "added"
    assert data["history"][1]["status"] == "modified"
