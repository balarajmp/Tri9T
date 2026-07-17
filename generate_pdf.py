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
        fontSize=28,
        leading=34,
        textColor=c_primary,
        alignment=TA_LEFT,
        spaceAfter=15
    )
    
    style_cover_subtitle = ParagraphStyle(
        'CoverSubtitle',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=13,
        leading=17,
        textColor=styles['Normal'].textColor,
        alignment=TA_LEFT,
        spaceAfter=40
    )
    
    style_cover_meta = ParagraphStyle(
        'CoverMeta',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=10,
        leading=15,
        textColor=colors.HexColor("#475569"),
        alignment=TA_LEFT
    )

    style_h1 = ParagraphStyle(
        'H1',
        parent=styles['Heading1'],
        fontName='Helvetica-Bold',
        fontSize=18,
        leading=22,
        textColor=c_primary,
        spaceBefore=16,
        spaceAfter=10,
        keepWithNext=True
    )
    
    style_h2 = ParagraphStyle(
        'H2',
        parent=styles['Heading2'],
        fontName='Helvetica-Bold',
        fontSize=13,
        leading=16,
        textColor=c_secondary,
        spaceBefore=12,
        spaceAfter=6,
        keepWithNext=True
    )

    style_body = ParagraphStyle(
        'Body',
        parent=styles['BodyText'],
        fontName='Helvetica',
        fontSize=9.5,
        leading=13.5,
        textColor=c_text,
        spaceAfter=6
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
        spaceAfter=4
    )
    
    style_code = ParagraphStyle(
        'CodeStyle',
        parent=styles['Normal'],
        fontName='Courier',
        fontSize=7.5,
        leading=9.5,
        textColor=colors.HexColor("#0F172A"),
        backColor=c_bg_light,
        borderColor=c_border,
        borderWidth=0.5,
        borderPadding=5,
        spaceAfter=8
    )
    
    style_table_header = ParagraphStyle(
        'TableHeaderText',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=8.5,
        leading=11,
        textColor=colors.white
    )
    
    style_table_cell = ParagraphStyle(
        'TableCellText',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=8,
        leading=10,
        textColor=c_text
    )

    story = []

    # ================= PAGE 1: COVER PAGE =================
    story.append(Spacer(1, 120))
    story.append(Paragraph("Engineering Approach & System Design Document", style_cover_title))
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
    <b>Prepared by:</b> Balaraj M P, BE Information Science and Engineering, CMR Institute of Technology<br/>
    <b>Status:</b> Final Submission<br/>
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
        [Paragraph("3. PDF Ingestion & Hierarchy Reconstruction", style_body_bold), Paragraph(". . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . .", style_body), Paragraph("Page 4", style_body_bold)],
        [Paragraph("4. Parser Edge Cases & Mitigations", style_body_bold), Paragraph(". . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . .", style_body), Paragraph("Page 4", style_body_bold)],
        [Paragraph("5. Validation Methodology", style_body_bold), Paragraph(". . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . .", style_body), Paragraph("Page 5", style_body_bold)],
        [Paragraph("6. Document Versioning & Matching Strategy", style_body_bold), Paragraph(". . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . .", style_body), Paragraph("Page 5", style_body_bold)],
        [Paragraph("7. Selection Management", style_body_bold), Paragraph(". . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . .", style_body), Paragraph("Page 6", style_body_bold)],
        [Paragraph("8. Structured LLM Generation & Pydantic Validation", style_body_bold), Paragraph(". . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . .", style_body), Paragraph("Page 6", style_body_bold)],
        [Paragraph("9. Stale Traceability Detection", style_body_bold), Paragraph(". . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . .", style_body), Paragraph("Page 6", style_body_bold)],
        [Paragraph("10. API Endpoint Documentation", style_body_bold), Paragraph(". . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . .", style_body), Paragraph("Page 7", style_body_bold)],
        [Paragraph("11. Unit Tests & Verification", style_body_bold), Paragraph(". . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . .", style_body), Paragraph("Page 8", style_body_bold)],
        [Paragraph("12. Technical Decision Log", style_body_bold), Paragraph(". . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . .", style_body), Paragraph("Page 8", style_body_bold)],
        [Paragraph("13. Known Limitations & Future Improvements", style_body_bold), Paragraph(". . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . .", style_body), Paragraph("Page 8", style_body_bold)],
    ]
    
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
    Tri9T is a professional automated verification platform designed to ingest complex technical PDF manuals, 
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
    story.append(Spacer(1, 10))
    
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
        [Paragraph("node_versions", style_table_cell), Paragraph("id (PK), logical_node_id (FK), document_version_id (FK), parent_logical_node_id (FK), title, content, content_hash", style_table_cell), Paragraph("Holds the actual text content, title, and SHA-256 hash of a node under a specific version.", style_table_cell)],
        [Paragraph("selections", style_table_cell), Paragraph("id (PK), document_version_id (FK), name", style_table_cell), Paragraph("A user-selected subset of logical nodes pinned to a document version.", style_table_cell)],
        [Paragraph("generated_test_cases", style_table_cell), Paragraph("id (PK), selection_id (FK), question, answer, reference_context", style_table_cell), Paragraph("Stores the validated, LLM-generated QA test cases linked to a selection.", style_table_cell)],
        [Paragraph("llm_generation_failures", style_table_cell), Paragraph("id (PK), selection_id (FK), raw_response, error_message", style_table_cell), Paragraph("Logs failed LLM outputs and schema validation errors for audits.", style_table_cell)],
    ]
    
    schema_table = Table(schema_details, colWidths=[100, 180, 224])
    schema_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), c_primary),
        ('GRID', (0,0), (-1,-1), 0.5, c_border),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, c_bg_light]),
        ('TOPPADDING', (0,0), (-1,-1), 4),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
    ]))
    story.append(schema_table)
    story.append(PageBreak())

    # ================= PAGE 4: PDF PARSING & EDGE CASES =================
    story.append(Paragraph("3. PDF Ingestion & Hierarchy Reconstruction", style_h1))
    parsing_intro = """
    Parsing complex layout specifications (like the CT200 user manual) requires a five-step extraction pipeline. 
    The core classes implemented inside <i>app/services/pdf_parser.py</i> are <b>LayoutAnalyzer</b>, <b>TableDetector</b>, 
    <b>BlockClassifier</b>, and <b>HierarchyBuilder</b>.
    """
    story.append(Paragraph(parsing_intro, style_body))
    
    story.append(Paragraph("<b>Spatial Bounding Box Filtering for Table Content Duplication</b>", style_body_bold))
    p_step1 = """
    The initial implementation duplicated table contents: cell text was parsed as tabular grids and also extracted 
    independently as standard text paragraphs. After visual verification, the <b>LayoutAnalyzer</b> was updated with bounding-box 
    filtering. The system computes the spatial center of every text block. If that center falls within the bounding box of 
    a detected table, the block is dropped from the paragraph stream, ensuring table cells are not duplicated.
    """
    story.append(Paragraph(p_step1, style_body))
    
    story.append(Paragraph("4. Parser Edge Cases & Mitigations", style_h1))
    
    edge_cases = [
        [Paragraph("<b>Edge Case Scenario</b>", style_table_header), Paragraph("<b>Pipeline Mitigation Strategy</b>", style_table_header)],
        [Paragraph("<b>Missing intermediate headings</b><br/>E.g. heading 3.1.2 appears but 3.1 was skipped.", style_table_cell), 
         Paragraph("The HierarchyBuilder detects the missing parent key, raises a hierarchy mismatch warning, and attaches the node to the longest matched prefix (e.g. heading 3.0 or root) to preserve order.", style_table_cell)],
        [Paragraph("<b>Page-boundary text split</b><br/>A paragraph breaks across page bounds.", style_table_cell), 
         Paragraph("Parser checks if the next block starts with a lowercase letter, a hyphen, or a list marker, automatically merging it into the previous paragraph block.", style_table_cell)],
        [Paragraph("<b>Duplicate headings</b><br/>Multiple headings share a key or name.", style_table_cell), 
         Paragraph("The system maintains local counters for each heading path and appends a duplicate suffix (<i>_dup[count]</i>) to enforce unique, stable logical signatures in the database.", style_table_cell)],
        [Paragraph("<b>Table text duplicate extraction</b><br/>Standard readers extract cell text twice.", style_table_cell), 
         Paragraph("The LayoutAnalyzer performs a spatial boundary check. If a text block's coordinate center falls within the bounding box of a detected table, it is dropped from the text stream.", style_table_cell)],
        [Paragraph("<b>Ordered list headings mismatch</b><br/>Numbered list items match heading patterns.", style_table_cell), 
         Paragraph("List items starting with numbering are filtered out from being headings if they exceed 80 characters, contain colons, or contain internal newlines.", style_table_cell)]
    ]
    
    edge_table = Table(edge_cases, colWidths=[180, 324])
    edge_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), c_primary),
        ('GRID', (0,0), (-1,-1), 0.5, c_border),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, c_bg_light]),
        ('TOPPADDING', (0,0), (-1,-1), 5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 5),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
    ]))
    story.append(edge_table)
    story.append(PageBreak())

    # ================= PAGE 5: VALIDATION & VERSIONING =================
    story.append(Paragraph("5. Validation Methodology", style_h1))
    val_text = """
    To verify that PDF parsing, table extraction, hierarchy builders, and version comparisons work correctly, the system incorporates the following checks:
    """
    story.append(Paragraph(val_text, style_body))
    
    val_1 = """<b>• Manual Outline Comparison:</b> Directly compared output JSON outline structures against the visual hierarchy of the source PDF files."""
    val_2 = """<b>• Visual Layout Analysis:</b> Rendered page blocks to verify correct column reading order and header/footer exclusion."""
    val_3 = """<b>• Hierarchy Verification:</b> Validated that sub-sections (e.g., 2.1.1.1) are correctly structured as children of 2.1.1, throwing warnings on mismatches."""
    val_4 = """<b>• Table and List Verification:</b> Verified cell alignment in pipe format and confirmed ordered list items do not pollute headings."""
    val_5 = """<b>• Version Match Audits:</b> Tested version diffing endpoints to verify they capture unchanged, modified, added, and removed nodes correctly."""
    val_6 = """<b>• Pytest Suite:</b> Isolated unit tests assert every pipeline class (LayoutAnalyzer, TableDetector, BlockClassifier, HierarchyBuilder) against synthetic inputs."""
    story.append(Paragraph(val_1, style_bullet))
    story.append(Paragraph(val_2, style_bullet))
    story.append(Paragraph(val_3, style_bullet))
    story.append(Paragraph(val_4, style_bullet))
    story.append(Paragraph(val_5, style_bullet))
    story.append(Paragraph(val_6, style_bullet))
    story.append(Spacer(1, 10))

    story.append(Paragraph("6. Document Versioning & Matching Strategy", style_h1))
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
        ('TOPPADDING', (0,0), (-1,-1), 4),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
    ]))
    story.append(matrix_table)
    story.append(PageBreak())

    # ================= PAGE 6: SELECTIONS & LLM PIPELINE =================
    story.append(Paragraph("7. Selection Management", style_h1))
    sel_text = """
    Users select logical nodes to pin baseline requirements.
    The primary routes are <b>POST /api/v1/selection</b> and <b>GET /api/v1/selection/{id}</b>.
    Selections remain <b>immutable</b> because they reference a specific <i>document_version_id</i> and the text content of those nodes at that time, protecting baselines from source manual modifications.
    """
    story.append(Paragraph(sel_text, style_body))
    
    story.append(Paragraph("8. Structured LLM Generation & Pydantic Validation", style_h1))
    llm_validation = """
    The Gemini model is prompted to act as a Senior QA Automation Engineer, receiving context and returning structured JSON matching a Pydantic schema:
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
  "required": ["test_cases"]
}"""
    story.append(Preformatted(schema_code, style_code))
    
    retry_text = """
    The system strips markdown formatting and validates the JSON structure. If validation fails, it executes <b>exactly one retry</b>. 
    If that also fails, the details are logged to <i>llm_generation_failures</i>, and an HTTP 422 error is returned.
    """
    story.append(Paragraph(retry_text, style_body))
    
    story.append(Paragraph("9. Stale Traceability Detection", style_h1))
    trace_text = """
    Upon manual revision ingestion, selection status is computed:
    """
    story.append(Paragraph(trace_text, style_body))
    tb_1 = """<b>• Fresh:</b> All selected logical nodes exist in the target version, and their content hashes (SHA-256) match."""
    tb_2 = """<b>• Possibly stale:</b> All selected nodes exist, but at least one node has a different content hash."""
    tb_3 = """<b>• Stale:</b> One or more selected nodes are completely missing (deleted) in the new version."""
    story.append(Paragraph(tb_1, style_bullet))
    story.append(Paragraph(tb_2, style_bullet))
    story.append(Paragraph(tb_3, style_bullet))
    
    stale_lims = """
    <b>Limitations of Hash Detection:</b> Hashing triggers false positives on minor cosmetic changes (spacing/punctuation), 
    misses semantic re-ordering context (false negatives), and is blind to sibling or parent heading updates.
    """
    story.append(Paragraph(stale_lims, style_body))
    story.append(PageBreak())

    # ================= PAGE 7: API ENDPOINT DOCUMENTATION =================
    story.append(Paragraph("10. API Endpoint Documentation", style_h1))
    
    # GET /documents
    story.append(Paragraph("<b>GET /api/v1/documents</b>", style_body_bold))
    story.append(Paragraph("• <i>Purpose:</i> Lists all ingested SQL documents.", style_body))
    story.append(Paragraph("• <i>Response:</i> <code>[{\"id\":1, \"name\":\"ct200_manual.pdf\"}]</code>", style_body))
    
    # GET /versions
    story.append(Paragraph("<b>GET /api/v1/versions</b>", style_body_bold))
    story.append(Paragraph("• <i>Purpose:</i> List all document versions. Supports <code>document_id</code> filter. (Note: <code>GET /documents/{version}</code> is not implemented directly; instead versions are browsed using <code>GET /api/v1/versions?document_id={id}</code>).", style_body))
    story.append(Paragraph("• <i>Response:</i> <code>[{\"id\":1, \"version_number\":1, \"commit_message\":\"Import\"}]</code>", style_body))
    
    # GET /nodes/{id}
    story.append(Paragraph("<b>GET /api/v1/nodes/{id}</b>", style_body_bold))
    story.append(Paragraph("• <i>Purpose:</i> Fetch details and historical node versions of a logical node by UUID.", style_body))
    story.append(Paragraph("• <i>Response:</i> <code>{\"id\":5, \"uuid\":\"abc-123\", \"node_versions\":[{\"id\":12, \"title\":\"Battery Life\"}]}</code>", style_body))
    
    # GET /search
    story.append(Paragraph("<b>GET /api/v1/search?q={query}</b>", style_body_bold))
    story.append(Paragraph("• <i>Purpose:</i> Performs search across outline nodes' contents.", style_body))
    
    # POST /selection & GET /selection/{id}
    story.append(Paragraph("<b>POST /api/v1/selection</b> & <b>GET /api/v1/selection/{id}</b>", style_body_bold))
    story.append(Paragraph("• <i>Purpose:</i> Create and retrieve selection sets. Selection route prefixes are singular in the implementation.", style_body))
    story.append(Paragraph("• <i>Request Payload:</i> <code>{\"name\":\"Specs\", \"document_version_id\":1, \"nodes\":[{\"node_id\":\"abc-123\"}]}</code>", style_body))
    
    # GET /generation/{selection_id} & GET /generation/node/{node_id}
    story.append(Paragraph("<b>GET /api/v1/generation/{selection_id}</b> & <b>GET /api/v1/generation/node/{node_id}</b>", style_body_bold))
    story.append(Paragraph("• <i>Purpose:</i> Retrieve generated test cases, versioning details, staleness status, and diff summaries. Prefix routes are singular in the implementation.", style_body))
    story.append(Paragraph("• <i>Response:</i> <code>{\"selection_id\":1, \"staleness_status\":\"Possibly stale\", \"test_cases\":[...]}</code>", style_body))
    
    story.append(PageBreak())

    # ================= PAGE 8: TESTS, DECISION LOG & LIMITATIONS =================
    story.append(Paragraph("11. Unit Tests & Verification", style_h1))
    test_intro = """
    The test suite verified:
    <b>• Deep Hierarchy:</b> Section 2.1.1.1 structures as a fourth-level child node (<i>test_heading_2_1_1_1_becomes_fourth_level_node</i>).
    <b>• Duplicate Headings:</b> Identical titles (Overview) produce unique stable keys and logical node UUIDs (<i>test_two_headings_with_identical_titles_produce_different_node_ids</i>).
    <b>• Reading Order:</b> Sections occurring out-of-order (3.4 before 3.3) preserve input reading sequence (<i>test_heading_3_4_appearing_before_3_3_preserves_reading_order</i>).
    <b>• Tables & Lists:</b> Verified Markdown pipe output and ensured ordered lists are not classified as headings.
    """
    story.append(Paragraph(test_intro, style_body))
    
    story.append(Paragraph("12. Technical Decision Log", style_h1))
    
    story.append(Paragraph("<b>Q1: What is the one part of this system most likely to silently give wrong results without erroring? How would you detect it?</b>", style_body_bold))
    q1_a = """
    <b>Answer:</b> The layout sorting and block classification. If bounding boxes are slightly off, the reader might sort sentences out of order or classify a heading as list text. It executes fine, but the hierarchy is corrupt.
    <i>Detection:</i> Render PDFs with debug overlay boxes (color-coded by classified block type), run structural sequence alerts (e.g. 2.1.2 followed by 2.1.9), and monitor text lengths statistically.
    """
    story.append(Paragraph(q1_a, style_body))
    
    story.append(Paragraph("<b>Q2: Where did you choose simplicity over correctness because of time? What would break first if this went to production?</b>", style_body_bold))
    q2_a = """
    <b>Answer:</b> Stable logical node signature matching. We use path signatures like <i>heading:2.1 > leaf:2.1_paragraph_1</i>. 
    <i>Production Failure:</i> If a new paragraph is inserted at the start of a section, all downstream siblings shift indexes, losing their logical identity. They are flagged as 'Removed'/'Added', causing their test cases to report 'Stale' falsely.
    """
    story.append(Paragraph(q2_a, style_body))
    
    story.append(Paragraph("<b>Q3: Name one input (parser, version matcher, or LLM call) that your implementation does NOT handle. What happens when it encounters it?</b>", style_body_bold))
    q3_a = """
    <b>Answer:</b> Multipage spanning tables and nested sub-tables.
    <i>Encounter behavior:</i> The TableDetector treats the table segments on subsequent pages as independent tables under their respective parent headings. Nested tables output malformed pipe markdown, cluttering structural text.
    """
    story.append(Paragraph(q3_a, style_body))
    
    story.append(Paragraph("13. Known Limitations & Future Improvements", style_h1))
    lims_imp = """
    <b>• Known Limitations:</b> Cosmetic changes trigger false-positive staleness reports; out-of-selection context modifications (parent updates) are missed.<br/>
    <b>• Future Improvements:</b> Calculate cosine similarity of embeddings to filter out cosmetic updates; compute relative outline hashes to detect hierarchy shifts; run LLM workers to auto-repair stale QA cases.
    """
    story.append(Paragraph(lims_imp, style_body))

    # Build the document
    doc.build(story, canvasmaker=NumberedCanvas)


if __name__ == "__main__":
    output_pdf = "Approach_Document.pdf"
    if len(sys.argv) > 1:
        output_pdf = sys.argv[1]
    
    print(f"Generating PDF: {output_pdf}...")
    create_approach_pdf(output_pdf)
    print("PDF generation complete!")
