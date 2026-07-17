from typing import List
from pydantic import BaseModel, ConfigDict, Field


class QATestCase(BaseModel):
    question: str = Field(
        ...,
        description="The question generated from the selected text content."
    )
    answer: str = Field(
        ...,
        description="The correct, precise answer to the question based on the selected text content."
    )
    reference_context: str = Field(
        ...,
        description="The exact text snippet or reference paragraph from the context that supports this QA test case."
    )


class QAGenerationResponse(BaseModel):
    test_cases: List[QATestCase] = Field(
        ...,
        min_length=3,
        max_length=5,
        description="A list containing 3 to 5 generated QA test cases."
    )

    model_config = ConfigDict(from_attributes=True)
