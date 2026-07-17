from fastapi import APIRouter, Depends, HTTPException, status
from app.api.deps import get_item_service
from app.schemas.item import ItemCreate, ItemResponse, ItemUpdate
from app.services.item_service import ItemService

router = APIRouter()


@router.get("", response_model=list[ItemResponse])
async def list_items(
    skip: int = 0,
    limit: int = 100,
    item_service: ItemService = Depends(get_item_service)
) -> list[ItemResponse]:
    """Retrieve a list of items with pagination."""
    items = await item_service.list_items(skip=skip, limit=limit)
    return list(items)


@router.get("/{item_id}", response_model=ItemResponse)
async def get_item(
    item_id: int,
    item_service: ItemService = Depends(get_item_service)
) -> ItemResponse:
    """Retrieve an item by its ID."""
    item = await item_service.get_item(item_id)
    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Item with ID {item_id} not found"
        )
    return item


@router.post("", response_model=ItemResponse, status_code=status.HTTP_201_CREATED)
async def create_item(
    item_in: ItemCreate,
    item_service: ItemService = Depends(get_item_service)
) -> ItemResponse:
    """Create a new item."""
    return await item_service.create_item(item_in)


@router.put("/{item_id}", response_model=ItemResponse)
async def update_item(
    item_id: int,
    item_in: ItemUpdate,
    item_service: ItemService = Depends(get_item_service)
) -> ItemResponse:
    """Update details of an existing item."""
    item = await item_service.update_item(item_id, item_in)
    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Item with ID {item_id} not found"
        )
    return item


@router.delete("/{item_id}", response_model=ItemResponse)
async def delete_item(
    item_id: int,
    item_service: ItemService = Depends(get_item_service)
) -> ItemResponse:
    """Remove an item from the system."""
    item = await item_service.delete_item(item_id)
    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Item with ID {item_id} not found"
        )
    return item
