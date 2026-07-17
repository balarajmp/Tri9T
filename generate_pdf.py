import os
import sys
from reportlab.lib.pagesizes import letter
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, KeepTogether, Preformatted
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.pdfgen import canvas
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY

class NumberedCanvas(canvas.Canvas):
    """
    Two-pass canvas to dynamically compute and render total page count,
    headers, and footers on all pages except the cover page.
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_decorations(num_pages)
            super().showPage()
        super().save()

    def draw_page_decorations(self, page_count):
        # Page 1 is the cover page - suppress header and footer
        if self._pageNumber == 1:
            return
        
        self.saveState()
        
        # Color definitions
        text_color = colors.HexColor("#475569")  # Slate gray
        border_color = colors.HexColor("#E2E8F0")  # Light gray divider
        
        self.setFont("Helvetica", 8)
        self.setFillColor(text_color)
        
        # Running Header
        self.drawString(54, 745, "Tri9T System Design & Engineering Approach")
        self.drawRightString(558, 745, "TECHNICAL DESIGN REPORT")
        self.setStrokeColor(border_color)
        self.setLineWidth(0.5)
        self.line(54, 737, 558, 737)
        
        # Running Footer
        page_text = f"Page {self._pageNumber} of {page_count}"
        self.drawString(54, 40, "CONFIDENTIAL - FOR INTERNAL USE ONLY")
        self.drawRightString(558, 40, page_text)
        self.line(54, 52, 558, 52)
        
        self.restoreState()


def create_approach_pdf(output_path):
    # Setup document geometry: 0.75 in (54 pt) side margins, 1 in (72 pt) top/bottom margins
    doc = SimpleDocTemplate(
        output_path,
        pagesize=letter,
        leftMargin=54,
        rightMargin=54,
        topMargin=72,
        bottomMargin=72
    )
    
    # Establish Design Tokens / Colors
    c_primary = colors.HexColor("#1E3A8A")   # Dark Navy
    c_secondary = colors.HexColor("#2563EB") # Royal Blue
    c_text = colors.HexColor("#1E293B")      # Charcoal
    c_bg_light = colors.HexColor("#F8FAFC")  # Off-white / light gray
    c_border = colors.HexColor("#E2E8F0")    # Divider gray
    
    # Create Styles
    styles = getSampleStyleSheet()
    
    # Custom Paragraph Styles
    style_cover_title = ParagraphStyle(
        'CoverTitle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=32,
        leading=38,
        textColor=c_primary,
        alignment=TA_LEFT,
        spaceAfter=15
    )
    
    style_cover_subtitle = ParagraphStyle(
        'CoverSubtitle',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=14,
        leading=18,
        textColor=styles['Normal'].textColor,
        alignment=TA_LEFT,
        spaceAfter=40
    )
    
    style_cover_meta = ParagraphStyle(
        'CoverMeta',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=10,
        leading=14,
        textColor=colors.HexColor("#64748B"),
        alignment=TA_LEFT
    )

    style_h1 = ParagraphStyle(
        'H1',
        parent=styles['Heading1'],
        fontName='Helvetica-Bold',
        fontSize=20,
        leading=24,
        textColor=c_primary,
        spaceBefore=18,
        spaceAfter=10,
        keepWithNext=True
    )
    
    style_h2 = ParagraphStyle(
        'H2',
        parent=styles['Heading2'],
        fontName='Helvetica-Bold',
        fontSize=14,
        leading=18,
        textColor=c_secondary,
        spaceBefore=14,
        spaceAfter=8,
        keepWithNext=True
    )

    style_body = ParagraphStyle(
        'Body',
        parent=styles['BodyText'],
        fontName='Helvetica',
        fontSize=10,
        leading=14,
        textColor=c_text,
        spaceAfter=8
    )
    
    style_body_bold = ParagraphStyle(
        'BodyBold',
        parent=style_body,
        fontName='Helvetica-Bold'
    )
    
    style_bullet = ParagraphStyle(
        'BulletText',
        parent=style_body,
        leftIndent=20,
        firstLineIndent=-10,
        spaceAfter=5
    )
    
    style_code = ParagraphStyle(
        'CodeStyle',
        parent=styles['Normal'],
        fontName='Courier',
        fontSize=8,
        leading=10,
        textColor=colors.HexColor("#0F172A"),
        backColor=c_bg_light,
        borderColor=c_border,
        borderWidth=0.5,
        borderPadding=6,
        spaceAfter=10
    )
    
    style_table_header = ParagraphStyle(
        'TableHeaderText',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=9,
        leading=12,
        textColor=colors.white
    )
    
    style_table_cell = ParagraphStyle(
        'TableCellText',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=8.5,
        leading=11,
        textColor=c_text
    )

    story = []

    # ================= PAGE 1: COVER PAGE =================
    story.append(Spacer(1, 120))
    story.append(Paragraph("Tri9T", style_cover_title))
    story.append(Paragraph("Document Versioning, Ingestion, and Verification Engine", style_cover_subtitle))
    
    # Colored accent bar
    accent_bar = Table([[""]], colWidths=[504], rowHeights=[4])
    accent_bar.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), c_secondary),
        ('PADDING', (0,0), (-1,-1), 0),
        ('BOTTOMPADDING', (0,0), (-1,-1), 0),
        ('TOPPADDING', (0,0), (-1,-1), 0),
    ]))
    story.append(accent_bar)
    story.append(Spacer(1, 150))
    
    # Metadata block
    meta_text = """
    <b>Prepared by:</b> Tri9T Backend Engineering Team<br/>
    <b>Status:</b> Production Verified<br/>
    <b>Document Version:</b> 1.0.0<br/>
    <b>Target Platform:</b> FastAPI + SQLite / MongoDB & Gemini LLM Pipeline<br/>
    <b>Date:</b> July 2026
    """
    story.append(Paragraph(meta_text, style_cover_meta))
    story.append(PageBreak())

    # ================= PAGE 2: TABLE OF CONTENTS & OVERVIEW =================
    story.append(Paragraph("Table of Contents", style_h1))
    story.append(Spacer(1, 10))
    
    toc_data = [
        [Paragraph("1. Executive Summary & System Architecture", style_body_bold), Paragraph(". . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . .", style_body), Paragraph("Page 3", style_body_bold)],
        [Paragraph("2. Relational Database Schema", style_body_bold), Paragraph(". . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . .", style_body), Paragraph("Page 3", style_body_bold)],
        [Paragraph("3. PDF Parsing & Hierarchy Reconstruction", style_body_bold), Paragraph(". . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . .", style_body), Paragraph("Page 4", style_body_bold)],
        [Paragraph("4. Parser Edge Cases & Mitigations", style_body_bold), Paragraph(". . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . .", style_body), Paragraph("Page 4", style_body_bold)],
        [Paragraph("5. Document Versioning & Matching Strategy", style_body_bold), Paragraph(". . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . .", style_body), Paragraph("Page 5", style_body_bold)],
        [Paragraph("6. Stale Traceability & Content Hash Detection", style_body_bold), Paragraph(". . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . .", style_body), Paragraph("Page 5", style_body_bold)],
        [Paragraph("7. LLM QA Generation & Retry Strategy", style_body_bold), Paragraph(". . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . .", style_body), Paragraph("Page 6", style_body_bold)],
        [Paragraph("8. Technical Decision Log", style_body_bold), Paragraph(". . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . .", style_body), Paragraph("Page 7", style_body_bold)],
        [Paragraph("9. Known Limitations & Future Improvements", style_body_bold), Paragraph(". . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . .", style_body), Paragraph("Page 7", style_body_bold)],
    ]
    
    # 504 total printable width: 140 width for title, 314 for dots, 50 for page
    toc_table = Table(toc_data, colWidths=[180, 264, 60])
    toc_table.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'BOTTOM'),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
        ('TOPPADDING', (0,0), (-1,-1), 4),
        ('LEFTPADDING', (0,0), (-1,-1), 0),
        ('RIGHTPADDING', (0,0), (-1,-1), 0),
    ]))
    story.append(toc_table)
    story.append(Spacer(1, 40))
    
    story.append(Paragraph("System Overview", style_h2))
    overview_text = """
    Tri9T is a production-grade automated verification platform designed to ingest complex technical PDF manuals, 
    reconstruct their hierarchical outline structure, and manage logical node revisions over time. 
    It enables QA test engineers to highlight specific sections of a manual, generate 3-5 high-fidelity test cases 
    using Gemini LLM structured outputs, and automatically trace the staleness of these test cases as updated 
    versions of the source manuals are uploaded.
    """
    story.append(Paragraph(overview_text, style_body))
    story.append(PageBreak())

    # ================= PAGE 3: ARCHITECTURE & SQL SCHEMA =================
    story.append(Paragraph("1. Executive Summary & System Architecture", style_h1))
    arch_intro = """
    The platform employs a clean, decoupled service architecture to separate core ingestion, validation, and retrieval tasks:
    """
    story.append(Paragraph(arch_intro, style_body))
    
    arch_bullet_1 = """<b>• API Router Layer:</b> Implements FastAPI routers for selections, document versions, node retrieval, and QA management. It strictly enforces Pydantic request and response models."""
    arch_bullet_2 = """<b>• Service Layer:</b> Orchestrates parsing logic (via PyMuPDF and PyTesseract), tree reconstruction (via Stack-based hierarchy parsing), version comparisons, and LLM retry pipelines."""
    arch_bullet_3 = """<b>• Persistence Layer:</b> Operates an asynchronous SQLite engine via aiosqlite for version control mappings, selections, and test case records. In parallel, MongoDB stores raw extracted page layouts and blocks."""
    story.append(Paragraph(arch_bullet_1, style_bullet))
    story.append(Paragraph(arch_bullet_2, style_bullet))
    story.append(Paragraph(arch_bullet_3, style_bullet))
    story.append(Spacer(1, 20))
    
    story.append(Paragraph("2. Relational Database Schema", style_h1))
    db_text = """
    The database tracks the evolution of document outlines across multiple manual uploads. Rather than tracking changes 
    line-by-line, the schema maps revisions to <b>Logical Nodes</b>. A logical node acts as a persistent anchor 
    with a stable UUID. When a new document version is imported, the system maps matching outline sections back to the 
    same logical node ID, creating a new NodeVersion record that links to the new DocumentVersion.
    """
    story.append(Paragraph(db_text, style_body))
    
    schema_details = [
        [Paragraph("<b>Table</b>", style_table_header), Paragraph("<b>Key Columns</b>", style_table_header), Paragraph("<b>Description</b>", style_table_header)],
        [Paragraph("documents", style_table_cell), Paragraph("id (PK), name", style_table_cell), Paragraph("Represents the root document profile.", style_table_cell)],
        [Paragraph("document_versions", style_table_cell), Paragraph("id (PK), document_id (FK), version_number, commit_message", style_table_cell), Paragraph("Captures a specific manual revision or upload transaction.", style_table_cell)],
        [Paragraph("logical_nodes", style_table_cell), Paragraph("id (PK), uuid, document_id (FK)", style_table_cell), Paragraph("Stable anchor representing a structural node across all document versions.", style_table_cell)],
        [Paragraph("node_versions", style_table_cell), Paragraph("id (PK), logical_node_id (FK), document_version_id (FK), title, content, content_hash", style_table_cell), Paragraph("Holds the actual text content, title, and SHA-256 hash of a node under a specific version.", style_table_cell)],
        [Paragraph("selections", style_table_cell), Paragraph("id (PK), document_version_id (FK), name", style_table_cell), Paragraph("A user-selected subset of logical nodes pinned to a document version.", style_table_cell)],
        [Paragraph("generated_test_cases", style_table_cell), Paragraph("id (PK), selection_id (FK), question, answer, reference_context", style_table_cell), Paragraph("Stores the validated, LLM-generated QA test cases linked to a selection.", style_table_cell)],
        [Paragraph("llm_generation_failures", style_table_cell), Paragraph("id (PK), selection_id (FK), raw_response, error_message", style_table_cell), Paragraph("Logs failed LLM outputs and schema validation errors for audits.", style_table_cell)],
    ]
    
    schema_table = Table(schema_details, colWidths=[100, 180, 224])
    schema_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), c_primary),
        ('GRID', (0,0), (-1,-1), 0.5, c_border),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, c_bg_light]),
        ('TOPPADDING', (0,0), (-1,-1), 6),
        ('BOTTOMPADDING', (0,0), (-1,-1), 6),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
    ]))
    story.append(schema_table)
    story.append(PageBreak())

    # ================= PAGE 4: PDF PARSING & EDGE CASES =================
    story.append(Paragraph("3. PDF Parsing & Hierarchy Reconstruction", style_h1))
    parsing_intro = """
    Parsing complex layout specifications (like the CT200 user manual) requires a five-step extraction pipeline:
    """
    story.append(Paragraph(parsing_intro, style_body))
    
    story.append(Paragraph("<b>Step 1: Raw Page Extraction & OCR Fallback</b>", style_body_bold))
    p_step1 = """
    Pages are extracted using PyMuPDF. If a page yields no digital characters (indicating a scanned image), 
    the system renders the page to a 150 DPI image and runs Tesseract OCR (pytesseract) to retrieve page text.
    """
    story.append(Paragraph(p_step1, style_body))
    
    story.append(Paragraph("<b>Step 2: Table Isolation</b>", style_body_bold))
    p_step2 = """
    PyMuPDF's table extraction locates cells. The TableDetector resolves overlapping or nested bounding boxes 
    by preserving only the largest enclosing table frame. Rows are formatted into clean Markdown grids.
    """
    story.append(Paragraph(p_step2, style_body))

    story.append(Paragraph("<b>Step 3: Geometry & Reading Order Alignment</b>", style_body_bold))
    p_step3 = """
    LayoutAnalyzer merges text blocks and tables. It discards any text block falling inside table boundaries 
    (to prevent duplicate table content extraction) and sorts all remaining elements top-to-bottom.
    """
    story.append(Paragraph(p_step3, style_body))

    story.append(Paragraph("<b>Step 4: Classification & Outline Stack Builder</b>", style_body_bold))
    p_step4 = """
    BlockClassifier identifies headings (dot-separated keys e.g. '2.1.1.1' or numbers like '1.'), lists, 
    and paragraphs. HierarchyBuilder merges paragraphs split across page boundaries and reconstructs the outline tree 
    using an ancestor tracking stack. Mismatched headings emit warnings without silently assigning faulty parents.
    """
    story.append(Paragraph(p_step4, style_body))
    story.append(Spacer(1, 10))

    story.append(Paragraph("4. Parser Edge Cases & Mitigations", style_h1))
    
    edge_cases = [
        [Paragraph("<b>Edge Case Scenario</b>", style_table_header), Paragraph("<b>Pipeline Mitigation Strategy</b>", style_table_header)],
        [Paragraph("<b>Missing intermediate headings</b><br/>E.g. heading 3.1.2 appears but 3.1 was skipped.", style_table_cell), 
         Paragraph("The HierarchyBuilder detects the missing parent key, raises a <i>Hierarchy mismatch</i> warning, and attaches the node to the longest matched prefix (e.g. heading 3.0 or root) to preserve order.", style_table_cell)],
        [Paragraph("<b>Page-boundary text split</b><br/>A paragraph breaks across page bounds.", style_table_cell), 
         Paragraph("Parser checks if the next block starts with a lowercase letter, a hyphen, or a list marker, automatically merging it into the previous paragraph block.", style_table_cell)],
        [Paragraph("<b>Duplicate headings</b><br/>Multiple headings share a key or name.", style_table_cell), 
         Paragraph("The system maintains local counters for each heading path and appends a duplicate suffix (<i>_dup[count]</i>) to enforce unique, stable logical signatures in the database.", style_table_cell)],
        [Paragraph("<b>Table text duplicate extraction</b><br/>Standard readers extract cell text twice.", style_table_cell), 
         Paragraph("The LayoutAnalyzer performs a spatial boundary check. If a text block's coordinate center falls within the bounding box of a detected table, it is dropped from the text stream.", style_table_cell)],
    ]
    
    edge_table = Table(edge_cases, colWidths=[180, 324])
    edge_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), c_primary),
        ('GRID', (0,0), (-1,-1), 0.5, c_border),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, c_bg_light]),
        ('TOPPADDING', (0,0), (-1,-1), 6),
        ('BOTTOMPADDING', (0,0), (-1,-1), 6),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
    ]))
    story.append(edge_table)
    story.append(PageBreak())

    # ================= PAGE 5: DOCUMENT VERSIONING & STALENESS =================
    story.append(Paragraph("5. Document Versioning & Matching Strategy", style_h1))
    version_text = """
    A key design requirement is recognizing logically identical nodes when a new document version is ingested. 
    Rather than performing character-based text alignment, the system maps outline nodes based on structural path signatures.
    """
    story.append(Paragraph(version_text, style_body))
    
    v_step1 = """<b>1. Path Signature Construction:</b> During manual ingestion, a signature string is generated for each node representing its type, heading hierarchy, and order index relative to its parent (e.g., <i>heading:2.0 > heading:2.1 > paragraph:3</i>)."""
    v_step2 = """<b>2. Map Alignment:</b> The signature is looked up in the previous version's signature-to-logical-node map (<i>prev_sig_map</i>)."""
    v_step3 = """<b>3. Identity Mapping:</b> If found, the node is associated with the existing <i>logical_node_id</i>. This preserves history across re-uploads. If missing, a new <i>logical_node_id</i> is created."""
    story.append(Paragraph(v_step1, style_bullet))
    story.append(Paragraph(v_step2, style_bullet))
    story.append(Paragraph(v_step3, style_bullet))
    story.append(Spacer(1, 10))

    story.append(Paragraph("Change Detection Rule Matrix", style_h2))
    
    matrix_data = [
        [Paragraph("<b>Scenario</b>", style_table_header), Paragraph("<b>Signature Path Match</b>", style_table_header), Paragraph("<b>Content Hash Match</b>", style_table_header), Paragraph("<b>Result Category</b>", style_table_header)],
        [Paragraph("Identity Preserved, No Change", style_table_cell), Paragraph("Matches Previous", style_table_cell), Paragraph("Identical", style_table_cell), Paragraph("<b>Unchanged</b>", style_table_cell)],
        [Paragraph("Node Relocated in Manual", style_table_cell), Paragraph("Different Path", style_table_cell), Paragraph("Identical", style_table_cell), Paragraph("<b>Unchanged (Moved)</b>", style_table_cell)],
        [Paragraph("Section Modified in Place", style_table_cell), Paragraph("Matches Previous", style_table_cell), Paragraph("Differs", style_table_cell), Paragraph("<b>Modified</b>", style_table_cell)],
        [Paragraph("New Section Introduced", style_table_cell), Paragraph("No Match (New)", style_table_cell), Paragraph("N/A", style_table_cell), Paragraph("<b>Added</b>", style_table_cell)],
        [Paragraph("Section Removed / Deleted", style_table_cell), Paragraph("No Match in V2", style_table_cell), Paragraph("N/A", style_table_cell), Paragraph("<b>Removed</b>", style_table_cell)],
    ]
    
    matrix_table = Table(matrix_data, colWidths=[140, 120, 120, 124])
    matrix_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), c_primary),
        ('GRID', (0,0), (-1,-1), 0.5, c_border),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, c_bg_light]),
        ('TOPPADDING', (0,0), (-1,-1), 5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 5),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
    ]))
    story.append(matrix_table)
    story.append(Spacer(1, 20))

    story.append(Paragraph("6. Stale Traceability & Content Hash Detection", style_h1))
    stale_text = """
    A user's selection contains reference text pinned to specific logical nodes. When a new version of the manual 
    is ingested, the system traces the selection validity by examining the state of the referenced nodes:
    """
    story.append(Paragraph(stale_text, style_body))
    
    stale_bullet_1 = """<b>• Fresh:</b> All selected logical nodes exist in the new version, and their content hashes (SHA-256) are identical to the source version."""
    stale_bullet_2 = """<b>• Possibly Stale:</b> All selected logical nodes exist in the new version, but the content hash of one or more nodes has changed (text updated)."""
    stale_bullet_3 = """<b>• Stale:</b> One or more of the selected logical nodes are entirely absent in the new version (the section was deleted)."""
    story.append(Paragraph(stale_bullet_1, style_bullet))
    story.append(Paragraph(stale_bullet_2, style_bullet))
    story.append(Paragraph(stale_bullet_3, style_bullet))
    
    stale_warn = """
    <i>Note on Hash-based Limits:</i> Content hashing is sensitive to character-level edits. Cosmetic corrections 
    (such as changing 'Safety Guidelines' to 'Safety Guideline') trigger a 'Possibly Stale' flag, even though 
    the underlying QA test cases remain semantically valid (False Positives).
    """
    story.append(Paragraph(stale_warn, style_body))
    story.append(PageBreak())

    # ================= PAGE 6: LLM & RETRY PIPELINE =================
    story.append(Paragraph("7. LLM QA Generation & Retry Strategy", style_h1))
    llm_intro = """
    The LLM integration transforms selection snippets into functional QA test cases. To guarantee safety and structure, 
    the generation pipeline is designed with strict boundaries:
    """
    story.append(Paragraph(llm_intro, style_body))

    story.append(Paragraph("Structured Output JSON Validation", style_h2))
    llm_validation = """
    The Gemini model is prompted to act as a Senior QA Automation Engineer. It is provided with the text context 
    and instructed to return a structured JSON response matching the following JSON Schema:
    """
    story.append(Paragraph(llm_validation, style_body))
    
    schema_code = """{
  "properties": {
    "test_cases": {
      "items": {
        "properties": {
          "question": { "type": "string" },
          "answer": { "type": "string" },
          "reference_context": { "type": "string" }
        },
        "required": ["question", "answer", "reference_context"],
        "type": "object"
      },
      "type": "array"
    }
  },
  "required": ["test_cases"],
  "type": "object"
}"""
    story.append(Preformatted(schema_code, style_code))
    
    story.append(Paragraph("Retry and Audit Execution Flow", style_h2))
    retry_text = """
    LLM outputs are cleaned of markdown formatting markers (like triple-backtick 'json') and parsed. 
    If a JSON parsing failure or a Pydantic schema validation error occurs, the system triggers <b>exactly one retry</b>. 
    If the retry also fails, the system logs the raw response and error string to the <i>llm_generation_failures</i> 
    table and returns an HTTP 422 error, providing transparency and audit capability.
    """
    story.append(Paragraph(retry_text, style_body))
    
    # Prompt Template box
    prompt_temp = """<b>Example System Instruction Prompt:</b>
You are a Senior QA Test Engineer. Generate 3-5 QA test cases directly based on the selected text.
Provide accurate factual answers derived ONLY from the provided text context. 
Your output MUST be a JSON object conforming to the QAGenerationResponse schema.
Do not include any conversational filler or preambles outside the JSON block."""
    story.append(Paragraph(prompt_temp, style_code))
    story.append(PageBreak())

    # ================= PAGE 7: DECISION LOG & FUTURE =================
    story.append(Paragraph("8. Technical Decision Log", style_h1))
    
    # Question 1
    story.append(Paragraph("<b>Q1: How does the system handle structural changes between versions?</b>", style_body_bold))
    q1_answer = """
    <b>Answer:</b> The system separates structural outline mapping from content payloads. Outline nodes are assigned stable 
    UUIDs on their first ingestion. Subsequent uploads resolve nodes against their parent outline paths (signatures) 
    rather than absolute coordinates or index lines. This isolates structural shifts (e.g. moving a section) from 
    content edits, allowing precise version history tracking.
    """
    story.append(Paragraph(q1_answer, style_body))
    story.append(Spacer(1, 10))

    # Question 2
    story.append(Paragraph("<b>Q2: Why was SQLite and SQL Schema chosen?</b>", style_body_bold))
    q2_answer = """
    <b>Answer:</b> The core requirements—document outlines, logical anchors, selection nodes, test cases, and audit trails—are 
    highly relational. A normalized SQL schema (using SQLAlchemy and SQLite with aiosqlite) enforces strict integrity, 
    provides clean join operations, and requires zero external daemon setup. This makes development, integration testing, 
    and local setups lightweight and reproducible. MongoDB is integrated in parallel as a secondary store for raw document layouts.
    """
    story.append(Paragraph(q2_answer, style_body))
    story.append(Spacer(1, 10))

    # Question 3
    story.append(Paragraph("<b>Q3: How is LLM integration validation structured?</b>", style_body_bold))
    q3_answer = """
    <b>Answer:</b> Raw LLM responses are parsed dynamically, stripped of markdown formatting blocks, and validated 
    using Pydantic models. A double-attempt execution path retries failures immediately. Persistent validation 
    failures are captured in the database (llm_generation_failures) rather than being silently dropped.
    """
    story.append(Paragraph(q3_answer, style_body))
    story.append(Spacer(1, 10))

    story.append(Paragraph("9. Known Limitations & Future Improvements", style_h1))
    
    story.append(Paragraph("<b>Known Limitations:</b>", style_body_bold))
    lim_1 = """<b>• Over-Sensitivity (False Positives):</b> Minor typo or spacing changes alter the content hash, marking selections as 'Possibly Stale' even if the test cases remain valid."""
    lim_2 = """<b>• Out-of-Selection Context Blindness:</b> If a sibling warning changes but the selected node remains identical, the selection status remains 'Fresh' despite potential semantic conflicts."""
    story.append(Paragraph(lim_1, style_bullet))
    story.append(Paragraph(lim_2, style_bullet))
    
    story.append(Paragraph("<b>Future Improvements:</b>", style_body_bold))
    imp_1 = """<b>• Semantic Similarity Scoring:</b> Calculate cosine similarity between text embeddings of original and new sections. Flag changes below 0.98 similarity as modified, ignoring minor typo fixes."""
    imp_2 = """<b>• AST & Relative Outline Hashing:</b> Hash the node's relative parent signature path along with the text. If a section is reordered, the selection status shifts to 'Possibly Stale' automatically."""
    imp_3 = """<b>• Auto-Repair Pipeline:</b> Add an LLM worker that parses 'Possibly Stale' selections and auto-corrects QA test cases to match the newly ingested version."""
    story.append(Paragraph(imp_1, style_bullet))
    story.append(Paragraph(imp_2, style_bullet))
    story.append(Paragraph(imp_3, style_bullet))

    # Build the document
    doc.build(story, canvasmaker=NumberedCanvas)


if __name__ == "__main__":
    output_pdf = "Approach_Document.pdf"
    if len(sys.argv) > 1:
        output_pdf = sys.argv[1]
    
    print(f"Generating PDF: {output_pdf}...")
    create_approach_pdf(output_pdf)
    print("PDF generation complete!")
