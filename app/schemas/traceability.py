from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field


class TraceabilityNodeDetail(BaseModel):
    logical_node_id: int
    logical_node_uuid: str
    status: str = Field(
        ...,
        description="Traceability status of the individual node: 'unchanged', 'modified', or 'removed'."
    )
    source_content_hash: Optional[str] = Field(
        None,
        description="The content hash of this node in the selection's pinned document version."
    )
    target_content_hash: Optional[str] = Field(
        None,
        description="The content hash of this node in the target document version."
    )


class TraceabilityResponse(BaseModel):
    status: str = Field(
        ...,
        description="Overall traceability status of the test cases: 'Fresh', 'Possibly stale', or 'Stale'."
    )
    source_version_id: int
    source_version_number: int
    target_version_id: int
    target_version_number: int
    nodes: List[TraceabilityNodeDetail] = Field(
        ...,
        description="Detailed, node-by-node traceability status report."
    )
    limitations: str = Field(
        ...,
        description="Detailed explanation of the limitations of hash-based stale detection."
    )

    model_config = ConfigDict(from_attributes=True)
