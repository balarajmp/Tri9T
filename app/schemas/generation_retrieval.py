from typing import List, Dict, Any, Optional
from pydantic import BaseModel, ConfigDict, Field


class RetrievalTestCase(BaseModel):
    id: int
    question: str
    answer: str
    reference_context: str

    model_config = ConfigDict(from_attributes=True)


class VersionMetadata(BaseModel):
    id: int
    version_number: int
    commit_message: Optional[str] = None
    created_at: Any

    model_config = ConfigDict(from_attributes=True)


class GenerationRetrievalResponse(BaseModel):
    selection_id: int
    selection_name: str
    original_version: VersionMetadata = Field(
        ...,
        description="The document version metadata when the selection and test cases were generated."
    )
    current_version: VersionMetadata = Field(
        ...,
        description="The latest document version metadata currently ingested."
    )
    staleness_status: str = Field(
        ...,
        description="The traceability status: 'Fresh', 'Possibly stale', or 'Stale'."
    )
    diff_summary: Dict[str, Any] = Field(
        ...,
        description="A summary of the differences for the selected nodes between original and current versions."
    )
    test_cases: List[RetrievalTestCase] = Field(
        ...,
        description="The list of successfully generated test cases."
    )

    model_config = ConfigDict(from_attributes=True)
