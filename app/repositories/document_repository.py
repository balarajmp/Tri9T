from motor.motor_asyncio import AsyncIOMotorDatabase
from app.repositories.nosql_repository import NoSQLRepository


class DocumentRepository(NoSQLRepository):
    """
    Specific repository class for NoSQL DocumentRecord entity.
    Inherits generic CRUD operations from NoSQLRepository and allows adding custom MongoDB pipeline/aggregation queries.
    """
    def __init__(self, db: AsyncIOMotorDatabase) -> None:
        super().__init__(collection_name="documents", db=db)

    # Custom queries (e.g. metadata text searches) can be added here
    async def get_by_filename(self, filename: str) -> list[dict]:
        """Fetch documents matching a specific filename exactly."""
        cursor = self.collection.find({"filename": filename})
        docs = []
        async for doc in cursor:
            doc["id"] = str(doc.pop("_id"))
            docs.append(doc)
        return docs
