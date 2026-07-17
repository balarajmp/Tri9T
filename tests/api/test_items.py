import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_create_and_get_item(client: AsyncClient) -> None:
    """Tests writing to and reading from the SQLite DB using FastAPI endpoints."""
    # 1. Create an item via HTTP POST
    payload = {"title": "Test Item", "description": "Test Description"}
    create_response = await client.post("/api/v1/items", json=payload)
    assert create_response.status_code == 201
    created_item = create_response.json()
    assert created_item["title"] == "Test Item"
    assert created_item["description"] == "Test Description"
    assert "id" in created_item
    assert created_item["is_active"] is True

    # 2. Retrieve the item via HTTP GET
    item_id = created_item["id"]
    get_response = await client.get(f"/api/v1/items/{item_id}")
    assert get_response.status_code == 200
    fetched_item = get_response.json()
    assert fetched_item["id"] == item_id
    assert fetched_item["title"] == "Test Item"
    assert fetched_item["description"] == "Test Description"
