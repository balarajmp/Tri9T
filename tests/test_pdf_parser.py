import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.services.pdf_parser import PDFParsingPipeline
from app.models.sql.document import Document, DocumentVersion
from app.models.sql.node import LogicalNode, NodeVersion


@pytest.mark.asyncio
async def test_pdf_parsing_pipeline_and_version_comparison(db_session: AsyncSession):
    """
    Verifies the PDF parsing pipeline on ct200_manual.pdf and ct200_manual_v2.pdf:
    - Parses document structure, headings, lists, tables, and paragraphs.
    - Resolves and reuses stable logical node identities (LogicalNode UUIDs) between versions.
    - Correctly detects content differences (e.g. battery life, error tables).
    """
    pipeline = PDFParsingPipeline()

    # 1. Parse Version 1 of the manual
    tree_v1 = pipeline.parse_pdf("ct200_manual.pdf", "CardioTrack CT-200 User Manual v1")
    assert tree_v1 is not None
    assert tree_v1["type"] == "document"
    assert "CardioTrack CT-200" in tree_v1["title"]

    # 2. Persist Version 1 to the database
    version_v1 = await pipeline.save_parsed_document(
        db=db_session,
        tree=tree_v1,
        doc_name="CardioTrack CT-200 Technical Manual",
        commit_message="Initial import of manual version 1"
    )
    await db_session.commit()

    assert version_v1.id is not None
    assert version_v1.version_number == 1

    # Query all NodeVersion records for v1
    stmt_v1 = (
        select(NodeVersion)
        .options(selectinload(NodeVersion.logical_node))
        .where(NodeVersion.document_version_id == version_v1.id)
    )
    res_v1 = await db_session.execute(stmt_v1)
    nvs_v1 = res_v1.scalars().all()
    assert len(nvs_v1) > 0

    # Find specific sections in v1
    battery_nv_v1 = next((nv for nv in nvs_v1 if "2.1.1.1" in nv.content), None)
    assert battery_nv_v1 is not None
    
    # Get the child paragraph of the 2.1.1.1 heading in v1
    battery_para_v1 = next((nv for nv in nvs_v1 if nv.parent_logical_node_id == battery_nv_v1.logical_node_id), None)
    assert battery_para_v1 is not None
    assert "300" in battery_para_v1.content or "300 measurement cycles" in battery_para_v1.content
    
    specs_table_v1 = next((nv for nv in nvs_v1 if nv.title == "Table" and "Pressure range" in nv.content), None)
    assert specs_table_v1 is not None
    assert "|" in specs_table_v1.content  # Markdown table format

    # 3. Parse Version 2 of the manual
    tree_v2 = pipeline.parse_pdf("ct200_manual_v2.pdf", "CardioTrack CT-200 User Manual v2")
    assert tree_v2 is not None

    # 4. Persist Version 2 to the database
    version_v2 = await pipeline.save_parsed_document(
        db=db_session,
        tree=tree_v2,
        doc_name="CardioTrack CT-200 Technical Manual",
        commit_message="Updated specs, added data export, revised battery estimates"
    )
    await db_session.commit()

    assert version_v2.id is not None
    assert version_v2.version_number == 2

    # Query all NodeVersion records for v2
    stmt_v2 = (
        select(NodeVersion)
        .options(selectinload(NodeVersion.logical_node))
        .where(NodeVersion.document_version_id == version_v2.id)
    )
    res_v2 = await db_session.execute(stmt_v2)
    nvs_v2 = res_v2.scalars().all()
    assert len(nvs_v2) > len(nvs_v1)  # Version 2 contains 5.3 Data Export, so it has more nodes

    # 5. Assert Node stable logical identity and differences
    # Let's match heading 2.1 General Specifications across versions
    heading_2_1_v1 = next((nv for nv in nvs_v1 if "2.1" in nv.content and "General Spec" in nv.title), None)
    heading_2_1_v2 = next((nv for nv in nvs_v2 if "2.1" in nv.content and "General Spec" in nv.title), None)
    
    assert heading_2_1_v1 is not None
    assert heading_2_1_v2 is not None
    # They MUST share the exact same logical_node UUID because of stable identity!
    assert heading_2_1_v1.logical_node.uuid == heading_2_1_v2.logical_node.uuid

    # Check 2.1.1.1 Battery Life
    battery_nv_v2 = next((nv for nv in nvs_v2 if "2.1.1.1" in nv.content), None)
    assert battery_nv_v2 is not None
    assert battery_nv_v1.logical_node.uuid == battery_nv_v2.logical_node.uuid

    # Check 2.1.1.1 Battery Life child paragraph
    battery_para_v2 = next((nv for nv in nvs_v2 if nv.parent_logical_node_id == battery_nv_v2.logical_node_id), None)
    assert battery_para_v2 is not None
    # Stable identity should hold for the paragraph node as well
    assert battery_para_v1.logical_node.uuid == battery_para_v2.logical_node.uuid
    # Content hash must be different because battery cycle estimate changed (300 -> 250)
    assert battery_para_v1.content_hash != battery_para_v2.content_hash

    # Check Section 5.3 Data Export (exists in v2, but not in v1)
    export_section_v1 = next((nv for nv in nvs_v1 if "5.3" in nv.content), None)
    export_section_v2 = next((nv for nv in nvs_v2 if "5.3" in nv.content), None)
    assert export_section_v1 is None
    assert export_section_v2 is not None
    assert "Data Export" in export_section_v2.title

    # Check that the Bluetooth error E6 is in v2 error codes table but not in v1
    err_table_v1 = next((nv for nv in nvs_v1 if nv.title == "Table" and "E1" in nv.content), None)
    err_table_v2 = next((nv for nv in nvs_v2 if nv.title == "Table" and "E1" in nv.content), None)
    
    assert err_table_v1 is not None
    assert err_table_v2 is not None
    assert "E6" not in err_table_v1.content
    assert "E6" in err_table_v2.content
    # They should have the same logical node identity since they are the same table in the same layout location!
    assert err_table_v1.logical_node.uuid == err_table_v2.logical_node.uuid
