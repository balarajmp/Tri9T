import asyncio
from collections.abc import AsyncGenerator
from typing import Any
import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from bson import ObjectId

from app.main import app
from app.core.database import Base, get_db_session, get_mongodb, mongodb_manager

# --- In-Memory Mock MongoDB implementation for isolated unit/integration tests ---

class MockCursor:
    def __init__(self, data: list[dict]) -> None:
        self.data = data
        self._skip = 0
        self._limit = None

    def skip(self, n: int) -> "MockCursor":
        self._skip = n
        return self

    def limit(self, n: int) -> "MockCursor":
        self._limit = n
        return self

    def __aiter__(self) -> "MockCursor":
        self.index = 0
        self.sliced_data = self.data[self._skip:]
        if self._limit is not None:
            self.sliced_data = self.sliced_data[:self._limit]
        return self

    async def __anext__(self) -> dict:
        if self.index < len(self.sliced_data):
            val = self.sliced_data[self.index]
            self.index += 1
            return val
        raise StopAsyncIteration


class MockInsertResult:
    def __init__(self, inserted_id: ObjectId) -> None:
        self.inserted_id = inserted_id


class MockDeleteResult:
    def __init__(self, deleted_count: int) -> None:
        self.deleted_count = deleted_count


class MockCollection:
    def __init__(self) -> None:
        self.documents: dict[ObjectId, dict] = {}

    async def find_one(self, filter: dict) -> dict | None:
        id_val = filter.get("_id")
        if isinstance(id_val, ObjectId):
            doc = self.documents.get(id_val)
            if doc:
                return {"_id": id_val, **doc}
        return None

    def find(self, filter: dict | None = None) -> MockCursor:
        docs = []
        for oid, doc in self.documents.items():
            if filter:
                match = True
                for k, v in filter.items():
                    # Handle basic nested filter checking or equality
                    if doc.get(k) != v:
                        match = False
                        break
                if match:
                    docs.append({"_id": oid, **doc})
            else:
                docs.append({"_id": oid, **doc})
        return MockCursor(docs)

    async def insert_one(self, document: dict) -> MockInsertResult:
        doc = document.copy()
        oid = doc.pop("_id", None)
        if oid is None:
            oid = ObjectId()
        self.documents[oid] = doc
        return MockInsertResult(oid)

    async def find_one_and_update(self, filter: dict, update: dict, return_document: bool = True) -> dict | None:
        id_val = filter.get("_id")
        if not isinstance(id_val, ObjectId):
            return None
        doc = self.documents.get(id_val)
        if not doc:
            return None
        
        set_fields = update.get("$set", {})
        for k, v in set_fields.items():
            doc[k] = v
            
        return {"_id": id_val, **doc}

    async def delete_one(self, filter: dict) -> MockDeleteResult:
        id_val = filter.get("_id")
        if isinstance(id_val, ObjectId) and id_val in self.documents:
            del self.documents[id_val]
            return MockDeleteResult(1)
        return MockDeleteResult(0)

    async def delete_many(self, filter: dict) -> MockDeleteResult:
        count = len(self.documents)
        self.documents.clear()
        return MockDeleteResult(count)


class MockDatabase:
    def __init__(self) -> None:
        self.collections: dict[str, MockCollection] = {}

    def __getitem__(self, name: str) -> MockCollection:
        if name not in self.collections:
            self.collections[name] = MockCollection()
        return self.collections[name]

    async def list_collection_names(self) -> list[str]:
        return list(self.collections.keys())


# --- Test Fixtures ---

# Isolated SQLite URL for testing (in-memory)
TEST_SQLITE_URL = "sqlite+aiosqlite:///:memory:"


@pytest_asyncio.fixture
async def test_engine():
    """Create an isolated SQLite database engine and initialize all tables."""
    engine = create_async_engine(
        TEST_SQLITE_URL,
        connect_args={"check_same_thread": False}
    )

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture
async def db_session(test_engine) -> AsyncGenerator[AsyncSession, None]:
    """Provide an isolated database session per test, automatically rolled back."""
    async_session = async_sessionmaker(
        test_engine,
        class_=AsyncSession,
        expire_on_commit=False
    )
    async with async_session() as session:
        yield session
        await session.rollback()


@pytest_asyncio.fixture
async def test_mongo_db() -> AsyncGenerator[Any, None]:
    """Provide an in-memory Mock MongoDB database instance. Clears collections between tests."""
    db = MockDatabase()
    yield db
    # Clear collections after each test to keep tests isolated
    collections = await db.list_collection_names()
    for col in collections:
        await db[col].delete_many({})


@pytest_asyncio.fixture
async def client(db_session, test_mongo_db) -> AsyncGenerator[AsyncClient, None]:
    """
    Provide an HTTPX async client connected to the FastAPI app.
    Dependencies (SQLAlchemy session and MongoDB database) are overridden.
    """
    # Override dependencies
    app.dependency_overrides[get_db_session] = lambda: db_session
    app.dependency_overrides[get_mongodb] = lambda: test_mongo_db

    # Temporarily bind the test mongo DB inside the manager to prevent startup crashes
    original_db = mongodb_manager.db
    mongodb_manager.db = test_mongo_db

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://testserver"
    ) as ac:
        yield ac

    # Clean up overrides
    app.dependency_overrides.clear()
    mongodb_manager.db = original_db
