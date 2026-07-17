from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from typing import Dict, Any, List, Optional
import logging

from app.models.sql.document import DocumentVersion
from app.models.sql.node import NodeVersion, LogicalNode

logger = logging.getLogger("app.services.version_comparison")


class VersionComparisonService:
    """
    Service layer responsible for comparing two DocumentVersion records,
    detecting unchanged, modified, added, and removed nodes based on stable
    logical node identities, heading paths, titles, and content hashes.
    """

    async def compare_document_versions(
        self, db: AsyncSession, v1_id: int, v2_id: int
    ) -> Dict[str, Any]:
        """
        Compares two versions of a document to find structural and content changes.
        Categorizes nodes as unchanged, modified, added, or removed.
        """
        # 1. Fetch document versions
        stmt_v1 = select(DocumentVersion).where(DocumentVersion.id == v1_id)
        res_v1 = await db.execute(stmt_v1)
        version_1 = res_v1.scalar_one_or_none()

        stmt_v2 = select(DocumentVersion).where(DocumentVersion.id == v2_id)
        res_v2 = await db.execute(stmt_v2)
        version_2 = res_v2.scalar_one_or_none()

        if not version_1 or not version_2:
            return {
                "error": f"One or both document versions (v1: {v1_id}, v2: {v2_id}) not found"
            }

        # 2. Fetch all node versions for both document versions
        stmt_nvs_v1 = (
            select(NodeVersion)
            .options(selectinload(NodeVersion.logical_node))
            .where(NodeVersion.document_version_id == v1_id)
        )
        res_nvs_v1 = await db.execute(stmt_nvs_v1)
        nvs_v1 = res_nvs_v1.scalars().all()

        stmt_nvs_v2 = (
            select(NodeVersion)
            .options(selectinload(NodeVersion.logical_node))
            .where(NodeVersion.document_version_id == v2_id)
        )
        res_nvs_v2 = await db.execute(stmt_nvs_v2)
        nvs_v2 = res_nvs_v2.scalars().all()

        # Map logical_node_id to NodeVersion for both versions
        nv_map_v1 = {nv.logical_node_id: nv for nv in nvs_v1}
        nv_map_v2 = {nv.logical_node_id: nv for nv in nvs_v2}

        # Helper to trace parent heading paths
        def _get_heading_path(nv: NodeVersion, nv_map: dict) -> str:
            path_segments = []
            curr_parent_id = nv.parent_logical_node_id
            while curr_parent_id in nv_map:
                parent_nv = nv_map[curr_parent_id]
                # Headings are nodes whose titles are not the default leaf names
                if parent_nv.title not in ("Table", "List", "Paragraph"):
                    path_segments.append(parent_nv.title)
                curr_parent_id = parent_nv.parent_logical_node_id
            
            path_segments.reverse()
            return " > ".join(path_segments) if path_segments else "root"

        comparison_results = []
        unchanged_count = 0
        modified_count = 0
        added_count = 0
        removed_count = 0

        # All logical node IDs across both versions
        all_logical_ids = set(nv_map_v1.keys()).union(set(nv_map_v2.keys()))

        for logical_id in all_logical_ids:
            nv1 = nv_map_v1.get(logical_id)
            nv2 = nv_map_v2.get(logical_id)

            if nv1 and nv2:
                # Exists in both: compare content hash
                path_v1 = _get_heading_path(nv1, nv_map_v1)
                path_v2 = _get_heading_path(nv2, nv_map_v2)
                
                # Check if heading path changed (indicating the node moved sections)
                is_moved = path_v1 != path_v2

                if nv1.content_hash == nv2.content_hash:
                    status = "unchanged"
                    unchanged_count += 1
                else:
                    status = "modified"
                    modified_count += 1

                comparison_results.append({
                    "logical_node_uuid": nv1.logical_node.uuid,
                    "title": nv2.title,
                    "type": "heading" if nv2.title not in ("Table", "List", "Paragraph") else nv2.title.lower(),
                    "status": status,
                    "is_moved": is_moved,
                    "v1_path": path_v1,
                    "v2_path": path_v2,
                    "v1_content": nv1.content,
                    "v2_content": nv2.content,
                    "v1_content_hash": nv1.content_hash,
                    "v2_content_hash": nv2.content_hash,
                })

            elif nv2:
                # Exists only in V2: Added
                path_v2 = _get_heading_path(nv2, nv_map_v2)
                added_count += 1
                comparison_results.append({
                    "logical_node_uuid": nv2.logical_node.uuid,
                    "title": nv2.title,
                    "type": "heading" if nv2.title not in ("Table", "List", "Paragraph") else nv2.title.lower(),
                    "status": "added",
                    "is_moved": False,
                    "v1_path": None,
                    "v2_path": path_v2,
                    "v1_content": None,
                    "v2_content": nv2.content,
                    "v1_content_hash": None,
                    "v2_content_hash": nv2.content_hash,
                })

            else:
                # Exists only in V1: Removed
                path_v1 = _get_heading_path(nv1, nv_map_v1)
                removed_count += 1
                comparison_results.append({
                    "logical_node_uuid": nv1.logical_node.uuid,
                    "title": nv1.title,
                    "type": "heading" if nv1.title not in ("Table", "List", "Paragraph") else nv1.title.lower(),
                    "status": "removed",
                    "is_moved": False,
                    "v1_path": path_v1,
                    "v2_path": None,
                    "v1_content": nv1.content,
                    "v2_content": None,
                    "v1_content_hash": nv1.content_hash,
                    "v2_content_hash": None,
                })

        return {
            "v1_version_number": version_1.version_number,
            "v2_version_number": version_2.version_number,
            "summary": {
                "unchanged_count": unchanged_count,
                "modified_count": modified_count,
                "added_count": added_count,
                "removed_count": removed_count,
            },
            "changes": comparison_results,
        }
