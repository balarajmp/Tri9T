import re
import io
import fitz
import hashlib
import logging
from uuid import uuid4
from typing import List, Dict, Any, Optional
from PIL import Image
import pytesseract
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.sql.document import Document, DocumentVersion
from app.models.sql.node import LogicalNode, NodeVersion

logger = logging.getLogger("app.services.pdf_parser")


class PDFReader:
    """
    Component 1: PDF Reader
    Responsible for opening the PDF, extracting page-by-page data, and 
    falling back to OCR using PyTesseract if no extractable text is present.
    """
    def __init__(self, tesseract_cmd: Optional[str] = None):
        if tesseract_cmd:
            pytesseract.pytesseract.tesseract_cmd = tesseract_cmd

    def extract_page_blocks(self, page: fitz.Page, page_num: int) -> List[tuple]:
        """
        Extracts raw text blocks from a page. If the page appears to be a scanned 
        image (i.e. has no text), it runs OCR.
        """
        blocks = page.get_text("blocks")
        # Filter blocks of type 0 (text blocks)
        text_blocks = [b for b in blocks if b[6] == 0]

        # Check if the page is completely scanned (no digital text found)
        page_text = page.get_text().strip()
        if not page_text:
            logger.info(f"Page {page_num} contains no extractable text. Attempting OCR...")
            ocr_text = self.run_ocr(page)
            if ocr_text.strip():
                # Treat OCR text as a single block spanning the page
                rect = page.rect
                text_blocks = [(rect.x0, rect.y0, rect.x1, rect.y1, ocr_text, 0, 0)]
            else:
                logger.warning(f"OCR returned no text for page {page_num}")
                text_blocks = []

        return text_blocks

    def run_ocr(self, page: fitz.Page) -> str:
        """
        Renders the page to a high-DPI image and runs OCR via Tesseract.
        Fails gracefully if Tesseract is not installed/configured on the host.
        """
        try:
            pix = page.get_pixmap(dpi=150)
            img_data = pix.tobytes("png")
            img = Image.open(io.BytesIO(img_data))
            return pytesseract.image_to_string(img)
        except Exception as e:
            logger.error(
                f"OCR failed: {e}. Please ensure Tesseract OCR is installed on the system."
            )
            return ""


class TableDetector:
    """
    Component 2: Table Detector
    Uses PyMuPDF's built-in table extraction. Implements geometric deduplication 
    to filter out duplicate sub-tables and nested tables.
    """
    def get_clean_tables(self, page: fitz.Page) -> List[Any]:
        """
        Finds tables on the page, and filters out overlapping/nested sub-tables 
        by keeping only the largest enclosing table bounding box.
        """
        try:
            tables = page.find_tables().tables
        except Exception as e:
            logger.error(f"Error extracting tables on page: {e}")
            return []

        if not tables:
            return []

        # Sort tables by bounding box area descending (largest first)
        sorted_tables = sorted(
            tables,
            key=lambda t: (t.bbox[2] - t.bbox[0]) * (t.bbox[3] - t.bbox[1]),
            reverse=True
        )

        kept_tables = []
        for t in sorted_tables:
            bbox_t = t.bbox
            contained = False
            for kt in kept_tables:
                bbox_kt = kt.bbox
                # Check if t is nested inside kt (with a 1.0 pt tolerance)
                if (bbox_kt[0] <= bbox_t[0] + 1.0 and
                    bbox_kt[1] <= bbox_t[1] + 1.0 and
                    bbox_kt[2] >= bbox_t[2] - 1.0 and
                    bbox_kt[3] >= bbox_t[3] - 1.0):
                    contained = True
                    break
            if not contained:
                kept_tables.append(t)

        return kept_tables

    def format_as_markdown(self, table_cells: List[List[str]]) -> str:
        """
        Converts raw 2D grid cells from a table extraction into clean, 
        standard Markdown table format.
        """
        if not table_cells or not table_cells[0]:
            return ""

        # Normalize content: replace internal newlines, strip spaces, escape pipes
        cleaned_rows = []
        for row in table_cells:
            cleaned_row = []
            for cell in row:
                cell_str = cell if cell is not None else ""
                cell_str = " ".join(cell_str.split())
                cell_str = cell_str.replace("|", "\\|")
                cleaned_row.append(cell_str)
            cleaned_rows.append(cleaned_row)

        headers = cleaned_rows[0]
        rows = cleaned_rows[1:]

        # Calculate max column widths for pretty alignment
        col_widths = [
            max(len(row[i]) for row in cleaned_rows) for i in range(len(headers))
        ]

        # Build lines
        header_line = "| " + " | ".join(headers[i].ljust(col_widths[i]) for i in range(len(headers))) + " |"
        sep_line = "| " + " | ".join("-" * col_widths[i] for i in range(len(headers))) + " |"
        body_lines = []
        for row in rows:
            body_lines.append("| " + " | ".join(row[i].ljust(col_widths[i]) for i in range(len(headers))) + " |")

        return "\n".join([header_line, sep_line] + body_lines)


class LayoutAnalyzer:
    """
    Component 3: Layout Analyzer
    Responsible for merging text blocks and tables on a page, removing text 
    blocks that fall inside table boundaries, and sorting the remaining 
    elements in reading order (top-to-bottom).
    """
    def merge_and_sort_elements(
        self, text_blocks: List[tuple], tables: List[Any]
    ) -> List[Dict[str, Any]]:
        elements = []

        # Convert tables to structured dicts
        table_bboxes = []
        for table in tables:
            table_bboxes.append(table.bbox)
            elements.append({
                "type": "table",
                "bbox": table.bbox,
                "cells": table.extract(),
                "y0": table.bbox[1]
            })

        # Process text blocks and exclude those inside tables
        for block in text_blocks:
            bx0, by0, bx1, by1, text, block_no, block_type = block
            block_bbox = (bx0, by0, bx1, by1)

            is_inside_table = False
            for t_bbox in table_bboxes:
                tx0, ty0, tx1, ty1 = t_bbox
                # Check for overlap: block is inside if >50% of its area is in table
                ix0 = max(bx0, tx0)
                iy0 = max(by0, ty0)
                ix1 = min(bx1, tx1)
                iy1 = min(by1, ty1)
                if ix1 > ix0 and iy1 > iy0:
                    intersection_area = (ix1 - ix0) * (iy1 - iy0)
                    block_area = (bx1 - bx0) * (by1 - by0)
                    if block_area > 0 and (intersection_area / block_area) > 0.5:
                        is_inside_table = True
                        break

            if not is_inside_table:
                elements.append({
                    "type": "text",
                    "bbox": block_bbox,
                    "content": text,
                    "y0": by0
                })

        # Sort elements by y0 (top-to-bottom reading order)
        elements.sort(key=lambda x: x["y0"])
        return elements


class BlockClassifier:
    """
    Component 4: Block Classifier
    Classifies raw layout blocks into heading, list_item, paragraph, or table elements.
    """
    # Matches hierarchical subsection headings (e.g. "2.1", "2.1.1.1")
    HEADING_SUB_PATTERN = re.compile(r"^\s*(\d+\.\d+(?:\.\d+)*)\s+(.*)", re.DOTALL)
    # Matches top-level headings (e.g. "1. Device Overview") but rejects lines with colons/long texts
    HEADING_TOP_PATTERN = re.compile(r"^\s*(\d+)\.\s+([^:\n]{1,80})$")
    # Matches list items (ordered e.g. "1. ", or bulleted e.g. "• ", "- ", "* ")
    ORDERED_LIST_PATTERN = re.compile(r"^\s*(\d+|[a-zA-Z])\.\s+(.*)", re.DOTALL)
    UNORDERED_LIST_PATTERN = re.compile(r"^\s*(•|\*|-)\s+(.*)", re.DOTALL)

    def classify_elements(self, raw_elements: List[Dict[str, Any]], table_detector: TableDetector) -> List[Dict[str, Any]]:
        classified = []
        for el in raw_elements:
            if el["type"] == "table":
                md_content = table_detector.format_as_markdown(el["cells"])
                classified.append({
                    "type": "table",
                    "content": md_content,
                    "bbox": el["bbox"],
                    "y0": el["y0"]
                })
                continue

            text = el["content"].strip()
            if not text:
                continue

            # Check sub-heading (e.g. 2.1, 2.1.1.1)
            sub_match = self.HEADING_SUB_PATTERN.match(text)
            if sub_match:
                key = sub_match.group(1)
                title = sub_match.group(2).replace("\n", " ").strip()
                level = len(key.split("."))
                classified.append({
                    "type": "heading",
                    "level": level,
                    "key": key,
                    "title": title,
                    "content": text,
                    "bbox": el["bbox"],
                    "y0": el["y0"]
                })
                continue

            # Check top heading (e.g. 1. Device Overview)
            top_match = self.HEADING_TOP_PATTERN.match(text)
            if top_match:
                key = top_match.group(1)
                title = top_match.group(2).replace("\n", " ").strip()
                classified.append({
                    "type": "heading",
                    "level": 1,
                    "key": key,
                    "title": title,
                    "content": text,
                    "bbox": el["bbox"],
                    "y0": el["y0"]
                })
                continue

            # Check ordered list item
            ordered_match = self.ORDERED_LIST_PATTERN.match(text)
            if ordered_match:
                marker = ordered_match.group(1)
                item_text = ordered_match.group(2).strip()
                classified.append({
                    "type": "list_item",
                    "list_type": "ordered",
                    "marker": marker,
                    "item_text": item_text,
                    "content": text,
                    "bbox": el["bbox"],
                    "y0": el["y0"]
                })
                continue

            # Check unordered list item
            unordered_match = self.UNORDERED_LIST_PATTERN.match(text)
            if unordered_match:
                marker = unordered_match.group(1)
                item_text = unordered_match.group(2).strip()
                classified.append({
                    "type": "list_item",
                    "list_type": "unordered",
                    "marker": marker,
                    "item_text": item_text,
                    "content": text,
                    "bbox": el["bbox"],
                    "y0": el["y0"]
                })
                continue

            # Default to paragraph
            classified.append({
                "type": "paragraph",
                "content": text,
                "bbox": el["bbox"],
                "y0": el["y0"]
            })

        return classified


class HierarchyBuilder:
    """
    Component 5: Hierarchy Builder
    Merges paragraphs split across page boundaries, groups consecutive list 
    items of the same type into a unified Markdown list block, and builds 
    a nested tree structure based on heading hierarchy.
    
    Ensures that parent-child relationships are inferred correctly and robustly.
    Never silently attaches nodes to incorrect parents.
    If hierarchy cannot be determined confidently (due to gaps or numbering mismatches),
    emits a warning instead of guessing.
    Supports unlimited heading depth.
    """
    def build_hierarchy(self, title: str, elements: List[Dict[str, Any]]) -> Dict[str, Any]:
        import warnings
        from collections import defaultdict

        # 1. Merge page-boundary splits
        cleaned = self._merge_page_boundaries(elements)

        # 2. Group list items
        grouped = self._group_list_items(cleaned)

        # 3. Build robust nested tree
        root = {
            "type": "document",
            "title": title,
            "content": "",
            "level": 0,
            "key": "root",
            "parent_key": None,
            "children": []
        }

        node_by_key = {"root": root}
        
        # Track counts of leaf child types per parent key to generate unique, stable keys
        leaf_counters = defaultdict(lambda: defaultdict(int))
        
        # Keep track of duplicate key counts to ensure uniqueness
        dup_counters = defaultdict(int)

        # Initialize stack with root
        stack = [root]

        for el in grouped:
            if el["type"] == "heading":
                key = el["key"]
                level = el["level"]
                
                # Identify the theoretical parent key
                if "." in key:
                    # e.g., "2.1.3" -> "2.1"
                    parent_key = ".".join(key.split(".")[:-1])
                else:
                    # e.g., "2" -> "root"
                    parent_key = "root"

                parent_key_actually_used = parent_key

                # Validate if the parent key exists
                if parent_key in node_by_key:
                    parent_node = node_by_key[parent_key]
                    # Check for level jumps (e.g. H1 to H3)
                    if level > parent_node["level"] + 1:
                        msg = (
                            f"Level jump detected: heading '{el['content']}' (key: '{key}', level {level}) "
                            f"directly follows parent '{parent_node['content'] or 'root'}' (level {parent_node['level']})."
                        )
                        warnings.warn(msg, UserWarning)
                        logger.warning(msg)
                else:
                    # Hierarchy cannot be determined confidently due to missing parent key!
                    msg = (
                        f"Hierarchy mismatch: heading '{el['content']}' (key: '{key}') "
                        f"expects parent key '{parent_key}', but '{parent_key}' was not found in the document tree."
                    )
                    warnings.warn(msg, UserWarning)
                    logger.warning(msg)
                    
                    # Instead of guessing an incorrect active parent, find the longest existing prefix
                    fallback_parent_key = "root"
                    if "." in key:
                        parts = key.split(".")
                        for i in range(len(parts) - 1, 0, -1):
                            prefix = ".".join(parts[:i])
                            if prefix in node_by_key:
                                fallback_parent_key = prefix
                                break
                    
                    parent_key_actually_used = fallback_parent_key
                    parent_node = node_by_key[fallback_parent_key]

                # Check for duplicate heading keys
                if key in node_by_key:
                    dup_counters[key] += 1
                    unique_key = f"{key}_dup{dup_counters[key]}"
                    msg = (
                        f"Duplicate heading key detected: '{key}' (content: '{el['content']}') already exists. "
                        f"Renaming to '{unique_key}' to ensure tree uniqueness."
                    )
                    warnings.warn(msg, UserWarning)
                    logger.warning(msg)
                    key = unique_key

                # Create the heading node
                node = {
                    "type": "heading",
                    "title": el["title"],
                    "content": el["content"],
                    "level": level,
                    "key": key,
                    "parent_key": parent_key_actually_used,
                    "children": []
                }
                
                # Attach to the resolved parent node
                parent_node["children"].append(node)
                
                # Register in the key map
                node_by_key[key] = node
                
                # Update stack to reflect the path from root to this node
                stack = self._get_ancestor_path(key, node_by_key)

            else:
                # Leaf node: paragraph, table, list
                # Leaf nodes always attach to the active heading at the top of the stack
                active_parent = stack[-1]
                parent_key = active_parent["key"]
                
                # Generate unique positional key for the leaf under its parent
                node_type = el["type"]
                count = leaf_counters[parent_key][node_type]
                leaf_counters[parent_key][node_type] += 1
                
                leaf_key = f"{parent_key}_{node_type}"
                if count > 0:
                    leaf_key = f"{leaf_key}_{count}"
                
                node = {
                    "type": node_type,
                    "title": node_type.capitalize(),
                    "content": el["content"],
                    "level": active_parent["level"] + 1,
                    "key": leaf_key,
                    "parent_key": parent_key,
                    "children": []
                }
                
                active_parent["children"].append(node)
                node_by_key[leaf_key] = node

        return root

    def _get_ancestor_path(self, node_key: str, node_by_key: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Traces back parent keys to construct a list of active ancestor nodes from root to node_key.
        """
        path = []
        curr_key = node_key
        while curr_key is not None and curr_key in node_by_key:
            node = node_by_key[curr_key]
            path.append(node)
            curr_key = node.get("parent_key")
        return list(reversed(path))

    def _merge_page_boundaries(self, elements: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        if not elements:
            return []

        merged = []
        for el in elements:
            if not merged:
                merged.append(el)
                continue

            prev = merged[-1]
            # If two consecutive elements are paragraphs, we check if they should be merged
            if prev["type"] == "paragraph" and el["type"] == "paragraph":
                prev_text = prev["content"].strip()
                should_merge = False

                # Rule A: Ends with hyphen (like "dis-")
                if prev_text.endswith("-"):
                    should_merge = True
                    prev_text = prev_text[:-1]  # remove hyphen
                # Rule B: Doesn't end in punctuation, and next starts with lowercase
                elif prev_text and not prev_text[-1] in (".", "!", "?", ":"):
                    should_merge = True
                elif el["content"].strip() and el["content"].strip()[0].islower():
                    should_merge = True

                if should_merge:
                    connector = "" if prev_text.endswith("-") else " "
                    prev["content"] = prev_text + connector + el["content"].strip()
                    prev["bbox"] = (
                        min(prev["bbox"][0], el["bbox"][0]),
                        prev["bbox"][1],
                        max(prev["bbox"][2], el["bbox"][2]),
                        el["bbox"][3]
                    )
                    continue

            merged.append(el)
        return merged

    def _group_list_items(self, elements: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        grouped = []
        current_list = []

        for el in elements:
            if el["type"] == "list_item":
                current_list.append(el)
            else:
                if current_list:
                    grouped.append(self._create_list_block(current_list))
                    current_list = []
                grouped.append(el)

        if current_list:
            grouped.append(self._create_list_block(current_list))

        return grouped

    def _create_list_block(self, items: List[Dict[str, Any]]) -> Dict[str, Any]:
        list_type = items[0]["list_type"]
        lines = []
        for item in items:
            marker = item["marker"]
            text = item["item_text"]
            if list_type == "ordered":
                lines.append(f"{marker}. {text}")
            else:
                lines.append(f"{marker} {text}")

        content = "\n".join(lines)
        bbox = (
            min(it["bbox"][0] for it in items),
            min(it["bbox"][1] for it in items),
            max(it["bbox"][2] for it in items),
            max(it["bbox"][3] for it in items)
        )
        return {
            "type": "list",
            "content": content,
            "bbox": bbox,
            "y0": items[0]["y0"]
        }


class PDFParsingPipeline:
    """
    Component 6: PDF Parsing Pipeline (Orchestrator)
    Coordinates reading, table extraction, layout sorting, classification, 
    and hierarchy construction. Saves the parsed document tree to the SQL 
    database, resolving and preserving logical node identities (UUIDs) across versions.
    """
    def __init__(self, tesseract_cmd: Optional[str] = None):
        self.reader = PDFReader(tesseract_cmd)
        self.table_detector = TableDetector()
        self.layout_analyzer = LayoutAnalyzer()
        self.classifier = BlockClassifier()
        self.builder = HierarchyBuilder()

    def parse_pdf(self, pdf_path: str, title: str) -> Dict[str, Any]:
        """
        Parses a PDF file into a clean, hierarchical tree dictionary.
        """
        doc = fitz.open(pdf_path)
        all_elements = []

        for page_num in range(len(doc)):
            page = doc[page_num]
            # 1. Extract raw text blocks
            text_blocks = self.reader.extract_page_blocks(page, page_num)
            # 2. Extract clean tables
            tables = self.table_detector.get_clean_tables(page)
            # 3. Merge & sort page elements in reading order
            page_elements = self.layout_analyzer.merge_and_sort_elements(text_blocks, tables)
            # 4. Classify elements (headings, tables, lists, paragraphs)
            classified_page_elements = self.classifier.classify_elements(page_elements, self.table_detector)
            all_elements.extend(classified_page_elements)

        doc.close()

        # 5. Group lists, merge splits, and build the nested tree
        tree = self.builder.build_hierarchy(title, all_elements)
        return tree

    async def save_parsed_document(
        self, db: AsyncSession, tree: Dict[str, Any], doc_name: str, commit_message: str = ""
    ) -> DocumentVersion:
        """
        Persists a parsed document tree to the SQL database using a single transaction.
        Correctly matches previous version nodes to reuse logical node identities (UUIDs).
        """
        # 1. Create or retrieve the root Document
        stmt_doc = select(Document).where(Document.name == doc_name)
        res_doc = await db.execute(stmt_doc)
        doc = res_doc.scalar_one_search() if hasattr(res_doc, "scalar_one_search") else res_doc.scalar_one_or_none()
        if not doc:
            doc = Document(name=doc_name)
            db.add(doc)
            await db.flush()

        # 2. Determine current version number
        stmt_version_count = select(DocumentVersion).where(DocumentVersion.document_id == doc.id)
        res_versions = await db.execute(stmt_version_count)
        existing_versions = res_versions.scalars().all()
        next_version_num = len(existing_versions) + 1

        # 3. Find previous version's logical node mappings if version > 1
        prev_sig_map = {}
        if existing_versions:
            # Sort by version number to find the latest previous version
            sorted_versions = sorted(existing_versions, key=lambda v: v.version_number)
            latest_prev_version = sorted_versions[-1]
            prev_sig_map = await self._get_logical_node_mappings(db, latest_prev_version.id)

        # 4. Create current DocumentVersion
        doc_version = DocumentVersion(
            document_id=doc.id,
            version_number=next_version_num,
            commit_message=commit_message
        )
        db.add(doc_version)
        await db.flush()

        # 5. Recursively save the tree nodes, matching with previous UUIDs or generating new ones
        await self._save_tree_node(
            db=db,
            doc_id=doc.id,
            version_id=doc_version.id,
            node=tree,
            parent_logical_id=None,
            prev_sig_map=prev_sig_map,
            sort_order=1
        )

        return doc_version

    async def _save_tree_node(
        self,
        db: AsyncSession,
        doc_id: int,
        version_id: int,
        node: Dict[str, Any],
        parent_logical_id: Optional[int],
        prev_sig_map: Dict[str, int],
        sort_order: int
    ) -> int:
        """
        Saves a node to the database (LogicalNode and NodeVersion).
        Matches logical node IDs from prev_sig_map. Returns the logical_node.id.
        """
        # Determine the logical signature for matching
        sig = self._get_node_signature(node)

        logical_node_id = prev_sig_map.get(sig)
        if logical_node_id:
            # Reuse existing LogicalNode
            logger.info(f"Reusing LogicalNode (ID: {logical_node_id}) for signature: {sig}")
        else:
            # Create a brand new LogicalNode
            new_uuid = str(uuid4())
            logical_node = LogicalNode(uuid=new_uuid, document_id=doc_id)
            db.add(logical_node)
            await db.flush()
            logical_node_id = logical_node.id
            logger.info(f"Created new LogicalNode (UUID: {new_uuid}) for signature: {sig}")

        # Compute content hash
        content = node["content"]
        content_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()

        # Create NodeVersion record
        node_version = NodeVersion(
            logical_node_id=logical_node_id,
            document_version_id=version_id,
            parent_logical_node_id=parent_logical_id,
            title=node["title"],
            content=content,
            content_hash=content_hash,
            sort_order=sort_order
        )
        db.add(node_version)
        await db.flush()

        # Recursively save children
        for idx, child in enumerate(node.get("children", [])):
            await self._save_tree_node(
                db=db,
                doc_id=doc_id,
                version_id=version_id,
                node=child,
                parent_logical_id=logical_node_id,
                prev_sig_map=prev_sig_map,
                sort_order=idx + 1
            )

        return logical_node_id

    def _get_node_signature(self, node: Dict[str, Any]) -> str:
        """
        Computes a stable structural signature for matching nodes across versions.
        """
        if node["type"] == "document":
            return "root"
        elif node["type"] == "heading":
            return f"heading:{node['key']}"
        else:
            # For non-heading nodes, we use the temporary key generated by build_hierarchy
            # which encodes the parent's heading key and the leaf type, e.g. "2.1_paragraph"
            # Since siblings of the same type under a parent are ordered, we include their index if possible.
            # But the generated key is stable enough as a positional identifier.
            return f"leaf:{node['key']}"

    async def _get_logical_node_mappings(self, db: AsyncSession, prev_version_id: int) -> Dict[str, int]:
        """
        Reconstructs node signatures and links them to logical_node_id for the 
        previous version's NodeVersions.
        """
        stmt = select(NodeVersion).where(NodeVersion.document_version_id == prev_version_id)
        res = await db.execute(stmt)
        nvs = res.scalars().all()

        # Map logical_node_id to NodeVersion
        nv_map = {nv.logical_node_id: nv for nv in nvs}

        # Find the root node version
        root_nv = next((nv for nv in nvs if nv.parent_logical_node_id is None), None)
        if not root_nv:
            return {}

        # Group children by parent_logical_node_id
        from collections import defaultdict
        children_by_parent = defaultdict(list)
        for nv in nvs:
            if nv.parent_logical_node_id is not None:
                children_by_parent[nv.parent_logical_node_id].append(nv)

        # Sort children by sort_order
        for parent_id in children_by_parent:
            children_by_parent[parent_id].sort(key=lambda x: x.sort_order)

        sig_map = {}

        def build_signatures(parent_id: int, parent_key: str):
            # We count leaf types to assign unique index-based keys to siblings
            leaf_counters = defaultdict(int)

            for nv in children_by_parent[parent_id]:
                # Identify if the NodeVersion represents a heading or a leaf
                sub_match = BlockClassifier.HEADING_SUB_PATTERN.match(nv.content)
                top_match = BlockClassifier.HEADING_TOP_PATTERN.match(nv.content)

                if sub_match or top_match:
                    key = sub_match.group(1) if sub_match else top_match.group(1)
                    sig = f"heading:{key}"
                    sig_map[sig] = nv.logical_node_id
                    build_signatures(nv.logical_node_id, key)
                else:
                    # Leaf node (paragraph, list, table)
                    node_type = "paragraph"
                    if nv.title == "Table":
                        node_type = "table"
                    elif nv.title == "List":
                        node_type = "list"

                    # Generate positional signature
                    sig = f"leaf:{parent_key}_{node_type}"
                    # If there are multiple leaf elements of same type, distinguish them
                    idx = leaf_counters[node_type]
                    leaf_counters[node_type] += 1
                    if idx > 0:
                        sig = f"{sig}_{idx}"

                    sig_map[sig] = nv.logical_node_id

        sig_map["root"] = root_nv.logical_node_id
        build_signatures(root_nv.logical_node_id, "root")
        return sig_map
