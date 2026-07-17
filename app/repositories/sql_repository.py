from typing import Any, Generic, Sequence, Type, TypeVar
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import Base
from app.repositories.base import BaseRepository

ModelType = TypeVar("ModelType", bound=Base)


class SQLRepository(Generic[ModelType], BaseRepository[ModelType]):
    """
    SQLAlchemy-specific repository implementing the generic BaseRepository interface.
    Handles primary CRUD operations asynchronously.
    """
    def __init__(self, model: Type[ModelType], db: AsyncSession) -> None:
        self.model = model
        self.db = db

    async def get(self, id: Any) -> ModelType | None:
        """Fetch a single model instance by its identifier."""
        return await self.db.get(self.model, id)

    async def get_all(self, skip: int = 0, limit: int = 100) -> Sequence[ModelType]:
        """Fetch multiple instances with pagination support."""
        stmt = select(self.model).offset(skip).limit(limit)
        result = await self.db.execute(stmt)
        return result.scalars().all()

    async def create(self, obj_in: Any) -> ModelType:
        """Create a new record in the database."""
        if isinstance(obj_in, dict):
            obj_data = obj_in
        else:
            obj_data = obj_in.model_dump()
        db_obj = self.model(**obj_data)
        self.db.add(db_obj)
        await self.db.flush()  # Populates ID but doesn't commit yet
        return db_obj

    async def update(self, db_obj: ModelType, obj_in: Any) -> ModelType:
        """Update an existing database record."""
        if isinstance(obj_in, dict):
            update_data = obj_in
        else:
            update_data = obj_in.model_dump(exclude_unset=True)

        for field in update_data:
            if hasattr(db_obj, field):
                setattr(db_obj, field, update_data[field])

        self.db.add(db_obj)
        await self.db.flush()
        return db_obj

    async def remove(self, id: Any) -> ModelType | None:
        """Delete a record by its identifier."""
        db_obj = await self.get(id)
        if db_obj:
            await self.db.delete(db_obj)
            await self.db.flush()
        return db_obj
