from pydantic import BaseModel, ConfigDict, Field


class DocumentBase(BaseModel):
    filename: str = Field(..., max_length=255, description="The original name of the document file")
    content_type: str = Field(..., description="The content/MIME type of the document")
    file_size_bytes: int = Field(..., gt=0, description="The size of the document in bytes")
    metadata_fields: dict = Field(default_factory=dict, description="Arbitrary custom metadata associated with the document")


class DocumentCreate(DocumentBase):
    pass


class DocumentUpdate(BaseModel):
    filename: str | None = Field(default=None, max_length=255, description="Updated filename")
    content_type: str | None = Field(default=None, description="Updated content type")
    file_size_bytes: int | None = Field(default=None, gt=0, description="Updated file size")
    metadata_fields: dict | None = Field(default=None, description="Updated metadata dictionary")


class DocumentResponse(DocumentBase):
    """Schema returned to API clients representing NoSQL documents."""
    id: str = Field(..., description="The stringified MongoDB ObjectId")

    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True
    )
