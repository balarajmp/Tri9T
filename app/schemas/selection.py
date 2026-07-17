from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field


class SelectionNodeCreate(BaseModel):
    node_id: str = Field(
        ...,
        description="The stable UUID or integer ID of the logical node."
    )
    selected_text: Optional[str] = Field(
        None,
        max_length=1000,
        description="Optional text snippet or annotation context selected within the node."
    )


class SelectionCreate(BaseModel):
    name: str = Field(
        ...,
        max_length=255,
        description="The name or label of the selection."
    )
    document_version_id: int = Field(
        ...,
        description="The ID of the document version this selection is pinned to."
    )
    nodes: List[SelectionNodeCreate] = Field(
        ...,
        min_length=1,
        description="The list of nodes and optional text selections to associate."
    )


class SelectionNodeResponse(BaseModel):
    logical_node_uuid: str = Field(..., description="Stable logical UUID of the node.")
    logical_node_id: int = Field(..., description="Database integer ID of the logical node.")
    title: Optional[str] = Field(None, description="Title of the node at the pinned version.")
    content: Optional[str] = Field(None, description="Content of the node at the pinned version.")
    selected_text: Optional[str] = Field(None, description="Captured selection text context.")

    model_config = ConfigDict(from_attributes=True)


class SelectionResponse(BaseModel):
    id: int = Field(..., description="Database ID of the selection.")
    name: str = Field(..., description="Name of the selection.")
    document_version_id: int = Field(..., description="ID of the associated document version.")
    version_number: int = Field(..., description="Version number of the document at time of selection.")
    document_name: str = Field(..., description="Name of the document.")
    created_at: datetime = Field(..., description="Timestamp when the selection was created.")
    updated_at: datetime = Field(..., description="Timestamp when the selection was last updated.")
    nodes: List[SelectionNodeResponse] = Field(..., description="List of nodes associated with the selection.")

    model_config = ConfigDict(from_attributes=True)
