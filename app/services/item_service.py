from typing import Sequence
from app.models.sql.item import Item
from app.repositories.item_repository import ItemRepository
from app.schemas.item import ItemCreate, ItemUpdate


class ItemService:
    """
    Service layer orchestrating all business logic around SQL Item entities.
    Mediates interaction between controllers/API endpoints and database access.
    """
    def __init__(self, repository: ItemRepository) -> None:
        self.repository = repository

    async def get_item(self, id: int) -> Item | None:
        """Retrieve an item by its ID."""
        return await self.repository.get(id)

    async def get_active_items(self, skip: int = 0, limit: int = 100) -> list[Item]:
        """Retrieve active items list."""
        return await self.repository.get_active_items(skip=skip, limit=limit)

    async def list_items(self, skip: int = 0, limit: int = 100) -> Sequence[Item]:
        """List all items with pagination."""
        return await self.repository.get_all(skip=skip, limit=limit)

    async def create_item(self, obj_in: ItemCreate) -> Item:
        """Create a new item entry."""
        return await self.repository.create(obj_in)

    async def update_item(self, id: int, obj_in: ItemUpdate) -> Item | None:
        """Update an existing item's details."""
        db_obj = await self.get_item(id)
        if not db_obj:
            return None
        return await self.repository.update(db_obj, obj_in)

    async def delete_item(self, id: int) -> Item | None:
        """Delete an item."""
        return await self.repository.remove(id)
