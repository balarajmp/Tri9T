import pytest
import hashlib
from uuid import uuid4
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.models.sql.document import Document, DocumentVersion
from app.models.sql.node import LogicalNode, NodeVersion
from app.models.sql.selection import Selection, SelectionNode


@pytest.mark.asyncio
async def test_document_versioning_and_hierarchy(db_session: AsyncSession):
    """
    Verifies that the database schema supports:
    - Root Document and incremental DocumentVersions.
    - LogicalNodes with stable logical identity (uuid).
    - NodeVersions capturing node state, hierarchy (parent_logical_node), and content hash per version.
    - Version-pinned Selections mapped to LogicalNodes.
    """
    # 1. Create a Document
    doc = Document(name="API System Design Specification")
    db_session.add(doc)
    await db_session.commit()
    await db_session.refresh(doc)
    assert doc.id is not None
    assert doc.name == "API System Design Specification"

    # 2. Create Document Version 1 (v1)
    v1 = DocumentVersion(
        document_id=doc.id,
        version_number=1,
        commit_message="Initial specification setup"
    )
    db_session.add(v1)
    await db_session.commit()
    await db_session.refresh(v1)
    assert v1.id is not None
    assert v1.version_number == 1

    # 3. Create Logical Nodes (stable identities)
    # Define Section 1 and Section 1.1
    sec1_uuid = str(uuid4())
    sec1_1_uuid = str(uuid4())

    logical_sec1 = LogicalNode(uuid=sec1_uuid, document_id=doc.id)
    logical_sec1_1 = LogicalNode(uuid=sec1_1_uuid, document_id=doc.id)
    db_session.add_all([logical_sec1, logical_sec1_1])
    await db_session.commit()
    await db_session.refresh(logical_sec1)
    await db_session.refresh(logical_sec1_1)
    assert logical_sec1.id is not None
    assert logical_sec1_1.id is not None

    # 4. Create Node Versions representing states for v1
    content_sec1 = "1. Introduction"
    hash_sec1 = hashlib.sha256(content_sec1.encode()).hexdigest()

    content_sec1_1 = "1.1 Goals and Non-Goals"
    hash_sec1_1 = hashlib.sha256(content_sec1_1.encode()).hexdigest()

    nv_sec1 = NodeVersion(
        logical_node_id=logical_sec1.id,
        document_version_id=v1.id,
        parent_logical_node_id=None,
        title="Introduction Section",
        content=content_sec1,
        content_hash=hash_sec1,
        sort_order=1
    )

    # Section 1.1 is defined as a child of Section 1
    nv_sec1_1 = NodeVersion(
        logical_node_id=logical_sec1_1.id,
        document_version_id=v1.id,
        parent_logical_node_id=logical_sec1.id,
        title="Goals Subsection",
        content=content_sec1_1,
        content_hash=hash_sec1_1,
        sort_order=1
    )

    db_session.add_all([nv_sec1, nv_sec1_1])
    await db_session.commit()

    # 5. Query and Assert Hierarchy for v1
    stmt = select(NodeVersion).where(NodeVersion.document_version_id == v1.id)
    result = await db_session.execute(stmt)
    node_versions = list(result.scalars().all())
    assert len(node_versions) == 2

    # Check child-parent link
    child_nv = next(nv for nv in node_versions if nv.logical_node_id == logical_sec1_1.id)
    assert child_nv.parent_logical_node_id == logical_sec1.id
    assert child_nv.content_hash == hash_sec1_1

    # 6. Create Document Version 2 (v2) where Section 1.1 moves to root (parent becomes None)
    v2 = DocumentVersion(
        document_id=doc.id,
        version_number=2,
        commit_message="Promoted goals subsection to root level"
    )
    db_session.add(v2)
    await db_session.commit()
    await db_session.refresh(v2)

    # Re-use logical node IDs (logical identity stays stable)
    nv2_sec1 = NodeVersion(
        logical_node_id=logical_sec1.id,
        document_version_id=v2.id,
        parent_logical_node_id=None,
        title="Introduction Section",
        content=content_sec1,  # content is same
        content_hash=hash_sec1,
        sort_order=1
    )

    nv2_sec1_1 = NodeVersion(
        logical_node_id=logical_sec1_1.id,
        document_version_id=v2.id,
        parent_logical_node_id=None,  # parent is now None (moved to root)
        title="Goals Section",        # title updated
        content="1.1 Goals and Scope Updates", # content updated
        content_hash=hashlib.sha256(b"1.1 Goals and Scope Updates").hexdigest(),
        sort_order=2
    )

    db_session.add_all([nv2_sec1, nv2_sec1_1])
    await db_session.commit()

    # Verify that in v1, the hierarchy remained intact, and in v2, it is flattened
    stmt_v1 = select(NodeVersion).where(
        NodeVersion.document_version_id == v1.id,
        NodeVersion.logical_node_id == logical_sec1_1.id
    )
    res_v1 = await db_session.execute(stmt_v1)
    nv1_state = res_v1.scalar_one()
    assert nv1_state.parent_logical_node_id == logical_sec1.id

    stmt_v2 = select(NodeVersion).where(
        NodeVersion.document_version_id == v2.id,
        NodeVersion.logical_node_id == logical_sec1_1.id
    )
    res_v2 = await db_session.execute(stmt_v2)
    nv2_state = res_v2.scalar_one()
    assert nv2_state.parent_logical_node_id is None
    assert nv2_state.title == "Goals Section"

    # 7. Create a Version-pinned Selection pinned to v1
    selection = Selection(name="Important highlight in v1", document_version_id=v1.id)
    db_session.add(selection)
    await db_session.commit()
    await db_session.refresh(selection)

    selection_node = SelectionNode(
        selection_id=selection.id,
        logical_node_id=logical_sec1_1.id,
        selected_text="Goals and Non-Goals"
    )
    db_session.add(selection_node)
    await db_session.commit()

    # Query back selection and verify selection is pinned to v1 context
    stmt_selection = (
        select(Selection)
        .options(selectinload(Selection.selection_nodes))
        .where(Selection.id == selection.id)
    )
    res_selection = await db_session.execute(stmt_selection)
    queried_selection = res_selection.scalar_one()
    assert queried_selection.document_version_id == v1.id
    assert len(queried_selection.selection_nodes) == 1
    assert queried_selection.selection_nodes[0].selected_text == "Goals and Non-Goals"
    assert queried_selection.selection_nodes[0].logical_node_id == logical_sec1_1.id
