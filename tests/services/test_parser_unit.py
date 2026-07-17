import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.services.pdf_parser import (
    BlockClassifier,
    HierarchyBuilder,
    TableDetector,
    LayoutAnalyzer,
    PDFParsingPipeline
)
from app.models.sql.node import NodeVersion


@pytest.fixture
def block_classifier():
    return BlockClassifier()


@pytest.fixture
def hierarchy_builder():
    return HierarchyBuilder()


@pytest.fixture
def table_detector():
    return TableDetector()


@pytest.fixture
def layout_analyzer():
    return LayoutAnalyzer()


def test_heading_2_1_1_1_becomes_fourth_level_node(hierarchy_builder):
    """
    1. Heading 2.1.1.1 becomes a fourth-level node.
    """
    elements = [
        {"type": "heading", "level": 1, "key": "2", "title": "General Specifications", "content": "2. General Specifications"},
        {"type": "heading", "level": 2, "key": "2.1", "title": "Battery", "content": "2.1 Battery"},
        {"type": "heading", "level": 3, "key": "2.1.1", "title": "Capacity", "content": "2.1.1 Capacity"},
        {"type": "heading", "level": 4, "key": "2.1.1.1", "title": "Battery Life Under Typical Use", "content": "2.1.1.1 Battery Life Under Typical Use"},
    ]
    tree = hierarchy_builder.build_hierarchy("Test Document", elements)
    
    # Verify the structure: Root -> 2 -> 2.1 -> 2.1.1 -> 2.1.1.1
    assert tree["type"] == "document"
    
    h2 = tree["children"][0]
    assert h2["key"] == "2"
    assert h2["level"] == 1
    
    h2_1 = h2["children"][0]
    assert h2_1["key"] == "2.1"
    assert h2_1["level"] == 2
    
    h2_1_1 = h2_1["children"][0]
    assert h2_1_1["key"] == "2.1.1"
    assert h2_1_1["level"] == 3
    
    h2_1_1_1 = h2_1_1["children"][0]
    assert h2_1_1_1["key"] == "2.1.1.1"
    assert h2_1_1_1["level"] == 4
    assert h2_1_1_1["type"] == "heading"
    assert h2_1_1_1["title"] == "Battery Life Under Typical Use"


@pytest.mark.asyncio
async def test_two_headings_with_identical_titles_produce_different_node_ids(db_session: AsyncSession):
    """
    2. Two headings with identical titles produce different node IDs/logical node UUIDs.
    """
    pipeline = PDFParsingPipeline()
    
    # We construct a tree containing multiple headings with the title "Overview"
    # - "1.1 Overview" (key: 1.1)
    # - "2.1 Overview" (key: 2.1)
    # - "3.1 Overview" (key: 3.1)
    # - A duplicate "3.1 Overview" which will get renamed to "3.1_dup1"
    tree = {
        "type": "document",
        "title": "Document Title",
        "content": "",
        "level": 0,
        "key": "root",
        "parent_key": None,
        "children": [
            {
                "type": "heading",
                "level": 1,
                "key": "1",
                "title": "Introduction",
                "content": "1. Introduction",
                "parent_key": "root",
                "children": [
                    {
                        "type": "heading",
                        "level": 2,
                        "key": "1.1",
                        "title": "Overview",
                        "content": "1.1 Overview",
                        "parent_key": "1",
                        "children": []
                    }
                ]
            },
            {
                "type": "heading",
                "level": 1,
                "key": "2",
                "title": "Specifications",
                "content": "2. Specifications",
                "parent_key": "root",
                "children": [
                    {
                        "type": "heading",
                        "level": 2,
                        "key": "2.1",
                        "title": "Overview",
                        "content": "2.1 Overview",
                        "parent_key": "2",
                        "children": []
                    }
                ]
            },
            {
                "type": "heading",
                "level": 1,
                "key": "3",
                "title": "System Settings",
                "content": "3. System Settings",
                "parent_key": "root",
                "children": [
                    {
                        "type": "heading",
                        "level": 2,
                        "key": "3.1",
                        "title": "Overview",
                        "content": "3.1 Overview",
                        "parent_key": "3",
                        "children": []
                    },
                    {
                        "type": "heading",
                        "level": 2,
                        "key": "3.1_dup1",
                        "title": "Overview",
                        "content": "3.1 Overview",
                        "parent_key": "3",
                        "children": []
                    }
                ]
            }
        ]
    }

    # Save to SQLite database
    version = await pipeline.save_parsed_document(
        db=db_session,
        tree=tree,
        doc_name="Identical Titles Manual",
        commit_message="Verifying identical titles"
    )
    await db_session.commit()

    # Query all NodeVersions for this document version
    stmt = (
        select(NodeVersion)
        .options(selectinload(NodeVersion.logical_node))
        .where(NodeVersion.document_version_id == version.id)
    )
    res = await db_session.execute(stmt)
    node_versions = res.scalars().all()

    # Filter node versions by title "Overview"
    overview_node_versions = [nv for nv in node_versions if nv.title == "Overview"]
    assert len(overview_node_versions) == 4

    # Extract database IDs and stable logical node UUIDs
    db_ids = [nv.id for nv in overview_node_versions]
    logical_node_ids = [nv.logical_node_id for nv in overview_node_versions]
    logical_node_uuids = [nv.logical_node.uuid for nv in overview_node_versions]

    # All IDs must be unique
    assert len(set(db_ids)) == 4
    assert len(set(logical_node_ids)) == 4
    assert len(set(logical_node_uuids)) == 4


def test_heading_3_4_appearing_before_3_3_preserves_reading_order(hierarchy_builder):
    """
    3. Heading 3.4 appearing before 3.3 preserves reading order.
    """
    elements = [
        {"type": "heading", "level": 1, "key": "3", "title": "Troubleshooting", "content": "3. Troubleshooting"},
        {"type": "heading", "level": 2, "key": "3.4", "title": "Advanced Diagnostics", "content": "3.4 Advanced Diagnostics"},
        {"type": "heading", "level": 2, "key": "3.3", "title": "Basic Diagnostics", "content": "3.3 Basic Diagnostics"},
    ]
    tree = hierarchy_builder.build_hierarchy("Test Document", elements)
    
    h3 = tree["children"][0]
    assert h3["key"] == "3"
    
    # Check that children of section 3 preserve the input (reading) order: 3.4 then 3.3
    children = h3["children"]
    assert len(children) == 2
    assert children[0]["key"] == "3.4"
    assert children[0]["title"] == "Advanced Diagnostics"
    
    assert children[1]["key"] == "3.3"
    assert children[1]["title"] == "Basic Diagnostics"


def test_tables_are_extracted_as_table_nodes(block_classifier, table_detector, hierarchy_builder):
    """
    4. Tables are extracted as table nodes.
    """
    raw_elements = [
        {
            "type": "heading",
            "bbox": (0, 0, 100, 20),
            "content": "1. Specifications",
            "y0": 0
        },
        {
            "type": "table",
            "bbox": (0, 30, 200, 100),
            "cells": [
                ["Parameter", "Specification"],
                ["Operating Temp", "10°C to 40°C"],
                ["Humidity", "30% to 75%"]
            ],
            "y0": 30
        }
    ]
    
    # 1. Classification
    classified = block_classifier.classify_elements(raw_elements, table_detector)
    assert len(classified) == 2
    assert classified[0]["type"] == "heading"
    assert classified[1]["type"] == "table"
    assert "|" in classified[1]["content"]  # formatted as markdown table
    
    # 2. Hierarchy Building
    tree = hierarchy_builder.build_hierarchy("Table Test Manual", classified)
    
    h1 = tree["children"][0]
    assert h1["key"] == "1"
    
    table_node = h1["children"][0]
    assert table_node["type"] == "table"
    assert table_node["title"] == "Table"
    assert "Operating Temp" in table_node["content"]
    assert "Humidity" in table_node["content"]


def test_ordered_lists_are_not_mistaken_for_headings(block_classifier, table_detector, hierarchy_builder):
    """
    5. Ordered lists are not mistaken for headings.
    """
    # Create text items representing typical ordered list items that should NOT match HEADING_TOP_PATTERN
    # e.g., >80 chars long, containing colon, containing newline, or letter-based prefix
    list_items = [
        "1. Turn on the CardioTrack CT-200 by pressing the power button firmly and wait for the LED display to turn blue.",  # > 80 chars
        "2. Note: Ensure the patient is sitting quietly in a comfortable chair and remains still during reading.",  # contains colon
        "3. Fit the cuff over the bare upper arm.\nKeep the bottom of the cuff 1-2 cm above the elbow.",  # contains newline
        "a. Secure the cuff with the hook and loop fastener."  # starts with alphabetical marker
    ]
    
    raw_elements = []
    for idx, text in enumerate(list_items):
        raw_elements.append({
            "type": "text",
            "bbox": (10, 50 + idx * 30, 300, 75 + idx * 30),
            "content": text,
            "y0": 50 + idx * 30
        })
        
    classified = block_classifier.classify_elements(raw_elements, table_detector)
    
    # Verify that block classifier classifies all of these as list_item and NOT heading
    for item in classified:
        assert item["type"] == "list_item", f"Incorrectly classified: {item}"
        
    # Verify that after hierarchy building they are correctly grouped as a list block under the instructions heading
    elements_with_heading = [
        {"type": "heading", "level": 1, "key": "1", "title": "Operation Instructions", "content": "1. Operation Instructions", "bbox": (10, 10, 100, 25), "y0": 10}
    ] + classified
    
    tree = hierarchy_builder.build_hierarchy("Manual Instructions", elements_with_heading)
    h1 = tree["children"][0]
    assert len(h1["children"]) == 1
    
    list_node = h1["children"][0]
    assert list_node["type"] == "list"
    assert list_node["title"] == "List"
    assert "Turn on the CardioTrack" in list_node["content"]
    assert "Ensure the patient is sitting" in list_node["content"]
    assert "Fit the cuff over the bare upper arm" in list_node["content"]
    assert "Secure the cuff with the hook" in list_node["content"]
