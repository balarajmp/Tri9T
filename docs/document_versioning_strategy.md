# Document Versioning and Comparison Strategy

This document details the strategy chosen to implement document versioning, track stable logical node identities, and compare different versions of parsed PDF manuals in the Tri9T system.

## Strategy Choice

To compare two versions of a document ($V_1$ and $V_2$) and categorize nodes as **unchanged**, **modified**, **added**, or **removed**, we use a multi-tiered identification and verification model based on four core anchors:

1. **Stable Logical Identity (`LogicalNode.uuid`)**: The primary anchor. As documents evolve, paragraphs might shift positions or edit content, but their logical role remains the same. During PDF parsing and import, our parser reconstructs position/heading-based signatures to resolve and reuse existing `LogicalNode` records.
2. **Heading Path**: Represents the structural hierarchy from the document root down to the parent of the node (e.g., `root > 2. General Specifications > 2.1 Battery`).
3. **Heading Title / Node Type**: The node's specific title (for sections) or structural role (e.g., `Paragraph`, `Table`, `List`).
4. **Content Hash**: A SHA-256 hash of the node's payload (e.g., text blocks, table markdown, list elements) to determine if modifications occurred.

### Why This Strategy Was Chosen

* **Resilience to Document Drift**: Documents rarely change completely at once. By tying changes to stable logical nodes and their hierarchical path (Heading Path), we avoid misalignment issues common in flat list line-by-line diffs (like Myers' diff), where inserting a single line at the top makes all subsequent lines look shifted.
* **Separation of Structure vs. Content**: Storing the hierarchical relationship separately from the text content allows us to detect when a node has been **moved** to a different section (`is_moved = True`) without its content actually changing.
* **Efficiency**: Content hashes (SHA-256) enable constant-time ($O(1)$) comparison of content bodies, bypassing the need to run expensive string-matching distance algorithms on every node in the tree.

---

## Change Classification Rules

Given node $N_1$ in $V_1$ and node $N_2$ in $V_2$ sharing the same `logical_node_id`:

| Scenario | Path Match | Content Hash Match | Category | Description |
| :--- | :--- | :--- | :--- | :--- |
| **$N_1$ exists, $N_2$ exists** | Same | Same | **Unchanged** | No edit, no move. |
| **$N_1$ exists, $N_2$ exists** | Different | Same | **Unchanged (Moved)** | The content is identical, but the node was moved to a different section (`is_moved=True`). |
| **$N_1$ exists, $N_2$ exists** | Any | Different | **Modified** | The text or data content changed. |
| **$N_1$ absent, $N_2$ exists** | N/A | N/A | **Added** | A brand new structural or leaf element. |
| **$N_1$ exists, $N_2$ absent** | N/A | N/A | **Removed** | An old node deleted in the new version. |

---

## Failure Cases & Mitigation

While highly robust, this strategy has distinct edge cases and failure modes:

### 1. Heading Renames & Cascading Path Shifts
* **The Failure**: If a high-level heading is renamed (e.g., `"2.1 Battery Specs"` $\rightarrow$ `"2.1 Battery Power"`), its title changes. Purely path-based matching will view this as the removal of the old heading and the addition of a new one. Consequently, all child nodes under this heading will see their heading paths shift, causing them to be flagged as moved or modified.
* **Mitigation**: Our pipeline prioritizes the database's `logical_node_id` matching. Since the parser maps the stable key (`heading:2.1`) to the same logical node during import, we preserve the identity of the section and all its children despite the title edit.

### 2. Duplicate Titles in the Same Section
* **The Failure**: If a section has multiple children with identical titles (e.g., two subsections named `"Overview"` under `"5. Troubleshooting"`), the path-based identifier is ambiguous, making it difficult to differentiate them.
* **Mitigation**: Our `HierarchyBuilder` detects duplicate heading keys in a single hierarchy run and appends `_dup[count]` to ensure uniqueness in logical node signatures.

### 3. Complete Structural Overhauls
* **The Failure**: If a document is completely restructured (e.g., merging section 2 and 3 and changing all layout coordinates), the positional signatures generated during parser execution will fail to match, causing old nodes to be marked as deleted and new ones created.
* **Mitigation**: A heuristic text-similarity fallback (like Levenshtein distance on text or Jaccard similarity on tables) could be integrated in the future to map orphaned nodes to new ones if the similarity is above a high threshold (e.g., 90%).
