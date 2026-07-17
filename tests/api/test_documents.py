import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_create_and_get_document(client: AsyncClient) -> None:
    """Tests creating and reading document metadata records from the MongoDB database."""
    # 1. Create a document record via POST
    payload = {
        "filename": "tax_report.pdf",
        "content_type": "application/pdf",
        "file_size_bytes": 204857,
        "metadata_fields": {"department": "finance", "year": 2026}
    }
    create_response = await client.post("/api/v1/documents", json=payload)
    assert create_response.status_code == 201
    created_doc = create_response.json()
    assert created_doc["filename"] == "tax_report.pdf"
    assert created_doc["file_size_bytes"] == 204857
    assert created_doc["metadata_fields"]["department"] == "finance"
    assert "id" in created_doc

    # 2. Retrieve the document record via GET
    doc_id = created_doc["id"]
    get_response = await client.get(f"/api/v1/documents/{doc_id}")
    assert get_response.status_code == 200
    fetched_doc = get_response.json()
    assert fetched_doc["id"] == doc_id
    assert fetched_doc["filename"] == "tax_report.pdf"
