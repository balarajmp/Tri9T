from sqlalchemy.ext.asyncio import AsyncSession
from app.models.sql.item import Item
from app.repositories.sql_repository import SQLRepository


class ItemRepository(SQLRepository[Item]):
    """
    Specific repository class for SQL Item entity.
    Inherits generic CRUD operations from SQLRepository and allows adding custom queries.
    """
    def __init__(self, db: AsyncSession) -> None:
        super().__init__(Item, db)

    # Custom queries (e.g. search, complex filters) can be added here
    async def get_active_items(self, skip: int = 0, limit: int = 100) -> list[Item]:
        """Fetch items that are currently active."""
        from sqlalchemy import select
        stmt = select(self.model).where(self.model.is_active == True).offset(skip).limit(limit)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())
