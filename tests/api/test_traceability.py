import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.sql.document import Document, DocumentVersion
from app.models.sql.node import LogicalNode, NodeVersion
from app.models.sql.selection import Selection, SelectionNode


@pytest.mark.asyncio
async def test_traceability_workflow(client: AsyncClient, db_session: AsyncSession):
    """
    Tests the traceability status endpoint.
    Covers Fresh, Possibly stale, and Stale transitions as document versions evolve.
    """
    # 1. Seed database with Document and Version 1
    doc = Document(name="Safety Manual")
    db_session.add(doc)
    await db_session.flush()

    v1 = DocumentVersion(document_id=doc.id, version_number=1, commit_message="V1 Base")
    db_session.add(v1)
    await db_session.flush()

    node_1 = LogicalNode(uuid="logical-a", document_id=doc.id)
    node_2 = LogicalNode(uuid="logical-b", document_id=doc.id)
    db_session.add_all([node_1, node_2])
    await db_session.flush()

    nv1_a = NodeVersion(
        logical_node_id=node_1.id,
        document_version_id=v1.id,
        parent_logical_node_id=None,
        title="Intro Section",
        content="Welcome to the manual.",
        content_hash="hash-intro-v1",
        sort_order=0
    )
    nv1_b = NodeVersion(
        logical_node_id=node_2.id,
        document_version_id=v1.id,
        parent_logical_node_id=None,
        title="Safety Section",
        content="Safety first.",
        content_hash="hash-safety-v1",
        sort_order=1
    )
    db_session.add_all([nv1_a, nv1_b])
    await db_session.flush()

    # 2. Create selection pinned to Version 1
    selection = Selection(name="Audit Selection", document_version_id=v1.id)
    db_session.add(selection)
    await db_session.flush()

    sn_a = SelectionNode(selection_id=selection.id, logical_node_id=node_1.id)
    sn_b = SelectionNode(selection_id=selection.id, logical_node_id=node_2.id)
    db_session.add_all([sn_a, sn_b])
    await db_session.commit()

    # --- Scenario 1: Trace against same version V1 (or latest = V1) ---
    response = await client.get(f"/api/v1/selection/{selection.id}/traceability")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "Fresh"
    assert data["source_version_number"] == 1
    assert data["target_version_number"] == 1
    assert len(data["nodes"]) == 2
    assert all(n["status"] == "unchanged" for n in data["nodes"])
    assert "Semantic Equivalence" in data["limitations"]

    # --- Scenario 2: Trace against V2 (Ingested unchanged) ---
    # Create Version 2 with identical content hashes
    v2 = DocumentVersion(document_id=doc.id, version_number=2, commit_message="V2 Minor formatting")
    db_session.add(v2)
    await db_session.flush()

    nv2_a = NodeVersion(
        logical_node_id=node_1.id,
        document_version_id=v2.id,
        parent_logical_node_id=None,
        title="Intro Section",
        content="Welcome to the manual.",
        content_hash="hash-intro-v1", # Unchanged
        sort_order=0
    )
    nv2_b = NodeVersion(
        logical_node_id=node_2.id,
        document_version_id=v2.id,
        parent_logical_node_id=None,
        title="Safety Section",
        content="Safety first.",
        content_hash="hash-safety-v1", # Unchanged
        sort_order=1
    )
    db_session.add_all([nv2_a, nv2_b])
    await db_session.commit()

    # Check status against Version 2 (which is now the latest)
    response_v2 = await client.get(f"/api/v1/selection/{selection.id}/traceability")
    assert response_v2.status_code == 200
    data_v2 = response_v2.json()
    assert data_v2["status"] == "Fresh"
    assert data_v2["target_version_number"] == 2

    # --- Scenario 3: Trace against V3 (Possibly stale - content modified) ---
    v3 = DocumentVersion(document_id=doc.id, version_number=3, commit_message="V3 Updates")
    db_session.add(v3)
    await db_session.flush()

    nv3_a = NodeVersion(
        logical_node_id=node_1.id,
        document_version_id=v3.id,
        parent_logical_node_id=None,
        title="Intro Section (Revised)",
        content="Welcome to the manual (updated).",
        content_hash="hash-intro-v3", # Modified
        sort_order=0
    )
    nv3_b = NodeVersion(
        logical_node_id=node_2.id,
        document_version_id=v3.id,
        parent_logical_node_id=None,
        title="Safety Section",
        content="Safety first.",
        content_hash="hash-safety-v1", # Unchanged
        sort_order=1
    )
    db_session.add_all([nv3_a, nv3_b])
    await db_session.commit()

    # Check status (latest is now V3)
    response_v3 = await client.get(f"/api/v1/selection/{selection.id}/traceability")
    assert response_v3.status_code == 200
    data_v3 = response_v3.json()
    assert data_v3["status"] == "Possibly stale"
    assert data_v3["target_version_number"] == 3

    # Check node details
    node_rev = next(n for n in data_v3["nodes"] if n["logical_node_uuid"] == "logical-a")
    assert node_rev["status"] == "modified"
    assert node_rev["source_content_hash"] == "hash-intro-v1"
    assert node_rev["target_content_hash"] == "hash-intro-v3"

    node_unrev = next(n for n in data_v3["nodes"] if n["logical_node_uuid"] == "logical-b")
    assert node_unrev["status"] == "unchanged"

    # --- Scenario 4: Trace against V4 (Stale - node removed) ---
    v4 = DocumentVersion(document_id=doc.id, version_number=4, commit_message="V4 Purge")
    db_session.add(v4)
    await db_session.flush()

    # Node 1 is removed in Version 4, only Node 2 is present
    nv4_b = NodeVersion(
        logical_node_id=node_2.id,
        document_version_id=v4.id,
        parent_logical_node_id=None,
        title="Safety Section",
        content="Safety first.",
        content_hash="hash-safety-v1",
        sort_order=0
    )
    db_session.add(nv4_b)
    await db_session.commit()

    # Check status (latest is V4)
    response_v4 = await client.get(f"/api/v1/selection/{selection.id}/traceability")
    assert response_v4.status_code == 200
    data_v4 = response_v4.json()
    assert data_v4["status"] == "Stale"
    assert data_v4["target_version_number"] == 4

    # Verify node details show removed
    node_removed = next(n for n in data_v4["nodes"] if n["logical_node_uuid"] == "logical-a")
    assert node_removed["status"] == "removed"
    assert node_removed["target_content_hash"] is None
