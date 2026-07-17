# Stale Traceability & Limitations of Hash-Based Detection

This document outlines the design decisions and technical limitations of using hash-based change detection for verifying the validity of generated QA test cases across document versions.

---

## 1. Stale Traceability Design

In this architecture, QA test cases are generated against a user-defined selection of document nodes (pinned to a specific source `document_version_id`). To assess if these test cases remain valid when a new document version is ingested, we inspect the changes in the selection's underlying nodes:

```mermaid
graph TD
    subgraph Version 1 (Source)
        S[Selection] --> SN_A[SelectionNode A]
        S --> SN_B[SelectionNode B]
        SN_A --> NV_A1[NodeVersion A1: Hash X]
        SN_B --> NV_B1[NodeVersion B1: Hash Y]
    end
    
    subgraph Version 2 (Target)
        NV_A2[NodeVersion A2: Hash X]
        NV_B2[NodeVersion B2: Hash Z]
    end
    
    NV_A1 -. Same Hash .-> NV_A2
    NV_B1 -. Different Hash .-> NV_B2
    
    style NV_A1 fill:#d4edda,stroke:#28a745
    style NV_A2 fill:#d4edda,stroke:#28a745
    style NV_B1 fill:#f8d7da,stroke:#dc3545
    style NV_B2 fill:#f8d7da,stroke:#dc3545
```

### Traceability Status States

*   **Fresh**: All nodes in the selection exist in the target document version and have identical content hashes to their source versions.
*   **Possibly stale**: All nodes in the selection exist in the target document version, but the content hash of at least one node has changed (indicating modified text).
*   **Stale**: One or more nodes in the selection have been completely deleted/removed from the target document version.

---

## 2. Limitations of Hash-Based Detection

While content hashes provide a fast, deterministic, and database-efficient mechanism for tracking changes, they suffer from inherent limitations when assessing the semantic validity of generated QAs:

### A. Semantic Equivalence (False Positives)
*   **The Issue**: Content hashing is sensitive to any byte-level change (whitespace, typo correction, punctuation changes, formatting).
*   **Impact**: If a node content is modified from *"The battery lasts 24 hrs."* to *"The battery lasts 24 hours."*, the content hash changes completely. The traceability state shifts to **Possibly stale**, yet the generated QA pair remains 100% correct.

### B. Out-of-Context Reordering (False Negatives)
*   **The Issue**: A node's content hash is computed strictly from its own title and body.
*   **Impact**: If Section 2.1 is moved under Section 5.3 (reordered) without any textual change, its content hash is identical. The system labels it **Fresh**, but the QA pair might now refer to obsolete structural context or contradict nearby sections.

### C. Parent & Sibling Dependencies (False Negatives)
*   **The Issue**: A test case generated for a node often implicitly depends on surrounding context (e.g., an introductory sentence in a parent heading or a constraint defined in a sibling paragraph).
*   **Impact**: If a parent node's content changes significantly but the selected node remains untouched, the selection reports **Fresh** based on unchanged hashes, failing to detect that the underlying QA test case is actually invalid.

### D. Lack of Intent Understanding
*   **The Issue**: A hash does not communicate *what* part of the sentence changed.
*   **Impact**: A change in a node could be unrelated to the generated question (e.g., modifying a section number vs. modifying a safety warning value). A hash treats both edits identically.

---

## 3. Recommended Future Mitigations

To overcome these limitations in a production deployment, we suggest combining hash-based detection with:

1.  **Semantic Similarity Analysis (embeddings)**: Compute cosine similarity between the source text and target text embeddings. If the similarity is above `0.98`, the change is likely cosmetic.
2.  **LLM-in-the-Loop Validation**: Use a lightweight LLM agent to review modified nodes against the generated QAs to check if the question/answer pair is still factually correct based on the new version.
3.  **AST / Hierarchy Path Tracking**: Incorporate the node's reconstructed hierarchy path into the hash check so that structural reordering shifts status to **Possibly stale**.
