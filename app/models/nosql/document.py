from pydantic import BaseModel, Field


class DocumentRecord(BaseModel):
    """
    Application-layer model representing a NoSQL document stored in MongoDB.
    Decoupled from MongoDB-specific BSON fields, utilizing standard types.
    """
    id: str | None = Field(default=None, description="Stringified MongoDB ObjectId")
    filename: str = Field(..., max_length=255, description="Original filename of the document")
    content_type: str = Field(..., description="MIME type of the document")
    file_size_bytes: int = Field(..., gt=0, description="Size of the file in bytes")
    metadata_fields: dict = Field(default_factory=dict, description="Arbitrary custom metadata fields")
