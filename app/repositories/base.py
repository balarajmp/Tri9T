from typing import Any, Generic, Sequence, TypeVar

T = TypeVar("T")


class BaseRepository(Generic[T]):
    """
    Abstract Base class/interface for all repositories.
    Provides generic signatures for standard CRUD operations.
    """
    async def get(self, id: Any) -> T | None:
        raise NotImplementedError

    async def get_all(self, skip: int = 0, limit: int = 100) -> Sequence[T]:
        raise NotImplementedError

    async def create(self, obj_in: Any) -> T:
        raise NotImplementedError

    async def update(self, db_obj: T, obj_in: Any) -> T:
        raise NotImplementedError

    async def remove(self, id: Any) -> T | None:
        raise NotImplementedError
