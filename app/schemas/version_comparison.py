from pydantic import BaseModel, Field
from typing import List, Optional


class ComparisonSummary(BaseModel):
    unchanged_count: int = Field(..., description="Number of nodes that did not change")
    modified_count: int = Field(..., description="Number of nodes with modified content")
    added_count: int = Field(..., description="Number of new nodes added in the new version")
    removed_count: int = Field(..., description="Number of nodes removed from the old version")


class NodeChange(BaseModel):
    logical_node_uuid: str = Field(..., description="The stable UUID of the logical node")
    title: str = Field(..., description="Title of the node")
    type: str = Field(..., description="Type of the node (heading, paragraph, table, list)")
    status: str = Field(..., description="Status of the change: unchanged, modified, added, or removed")
    is_moved: bool = Field(..., description="Whether the structural heading path changed")
    v1_path: Optional[str] = Field(None, description="The structural path in Version 1")
    v2_path: Optional[str] = Field(None, description="The structural path in Version 2")
    v1_content: Optional[str] = Field(None, description="The content in Version 1")
    v2_content: Optional[str] = Field(None, description="The content in Version 2")
    v1_content_hash: Optional[str] = Field(None, description="Content hash in Version 1")
    v2_content_hash: Optional[str] = Field(None, description="Content hash in Version 2")


class VersionComparisonResponse(BaseModel):
    v1_version_number: int = Field(..., description="Version number of V1")
    v2_version_number: int = Field(..., description="Version number of V2")
    summary: ComparisonSummary = Field(..., description="Summary counts of change statuses")
    changes: List[NodeChange] = Field(..., description="Detailed changes list per logical node")
