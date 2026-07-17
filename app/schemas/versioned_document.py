from pydantic import BaseModel, ConfigDict, Field
from datetime import datetime
from typing import List, Optional


class SQLDocumentResponse(BaseModel):
    id: int = Field(..., description="Unique integer ID of the SQL Document")
    name: str = Field(..., description="Display name of the document")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")

    model_config = ConfigDict(from_attributes=True)


class DocumentVersionResponse(BaseModel):
    id: int = Field(..., description="Unique integer ID of the Document Version record")
    document_id: int = Field(..., description="Associated Document integer ID")
    version_number: int = Field(..., description="Incremental version number")
    commit_message: Optional[str] = Field(None, description="Optional description of changes in this version")
    created_at: datetime = Field(..., description="Timestamp of when the version was saved")

    model_config = ConfigDict(from_attributes=True)


class NodeVersionBrief(BaseModel):
    id: int
    document_version_id: int
    version_number: int
    parent_logical_node_uuid: Optional[str] = None
    title: str
    content: str
    content_hash: str
    sort_order: int

    model_config = ConfigDict(from_attributes=True)


class LogicalNodeResponse(BaseModel):
    id: int = Field(..., description="Database primary key integer ID")
    uuid: str = Field(..., description="Stable UUID of the logical node")
    document_id: int = Field(..., description="Document ID the node belongs to")
    node_versions: List[NodeVersionBrief] = Field(default_factory=list, description="All historic versions of this logical node")

    model_config = ConfigDict(from_attributes=True)


class NodeVersionResponse(BaseModel):
    id: int
    logical_node_uuid: str
    document_version_id: int
    version_number: int
    parent_logical_node_uuid: Optional[str] = None
    title: str
    content: str
    content_hash: str
    sort_order: int

    model_config = ConfigDict(from_attributes=True)


class SearchResultNode(BaseModel):
    logical_node_uuid: str = Field(..., description="Stable UUID of the matched logical node")
    document_id: int = Field(..., description="SQL Document ID")
    document_name: str = Field(..., description="Name of the document")
    document_version_id: int = Field(..., description="SQL Document Version ID")
    version_number: int = Field(..., description="Incremental version number of the document")
    title: str = Field(..., description="Matched node title")
    content: str = Field(..., description="Matched node content preview")
    content_hash: str = Field(..., description="Payload content hash")

    model_config = ConfigDict(from_attributes=True)


class SearchResponse(BaseModel):
    results: List[SearchResultNode] = Field(default_factory=list, description="List of matched nodes")
    total_matches: int = Field(..., description="Total count of search results")


class NodeHistoryItem(BaseModel):
    document_version_id: int = Field(..., description="SQL Document Version ID")
    version_number: int = Field(..., description="Version number of the document")
    commit_message: Optional[str] = Field(None, description="Commit message of the version")
    created_at: datetime = Field(..., description="Version creation timestamp")
    title: str = Field(..., description="Node title at this version")
    content: str = Field(..., description="Node content at this version")
    content_hash: str = Field(..., description="Node content hash at this version")
    parent_logical_node_uuid: Optional[str] = Field(None, description="Parent logical node UUID at this version")
    status: str = Field(..., description="Change status relative to the previous version (added, modified, or unchanged)")

    model_config = ConfigDict(from_attributes=True)


class NodeHistoryResponse(BaseModel):
    logical_node_uuid: str = Field(..., description="Stable UUID of the logical node")
    document_id: int = Field(..., description="SQL Document ID")
    history: List[NodeHistoryItem] = Field(default_factory=list, description="Chronological history of changes for this node")
