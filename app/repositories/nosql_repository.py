from typing import Any, Dict, List, TypeVar
from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase

T = TypeVar("T")  # Represents the Pydantic schema or type of the stored document


class NoSQLRepository:
    """
    MongoDB-specific repository mapping base data access operations to Motor async operations.
    Handles serialization of BSON ObjectIds to string IDs.
    """
    def __init__(self, collection_name: str, db: AsyncIOMotorDatabase) -> None:
        self.db = db
        self.collection = db[collection_name]

    async def get(self, id: str) -> Dict[str, Any] | None:
        """Fetch a single document by stringified ObjectId."""
        if not ObjectId.is_valid(id):
            return None
        doc = await self.collection.find_one({"_id": ObjectId(id)})
        if doc:
            doc["id"] = str(doc.pop("_id"))
            return doc
        return None

    async def get_all(self, skip: int = 0, limit: int = 100) -> List[Dict[str, Any]]:
        """Fetch multiple documents with pagination."""
        cursor = self.collection.find().skip(skip).limit(limit)
        docs = []
        async for doc in cursor:
            doc["id"] = str(doc.pop("_id"))
            docs.append(doc)
        return docs

    async def create(self, obj_in: Any) -> Dict[str, Any]:
        """Insert a document into the collection."""
        if not isinstance(obj_in, dict):
            obj_data = obj_in.model_dump()
        else:
            obj_data = obj_in.copy()

        # Handle explicit 'id' to '_id' conversion if needed
        if "id" in obj_data:
            obj_id = obj_data.pop("id")
            if obj_id and ObjectId.is_valid(obj_id):
                obj_data["_id"] = ObjectId(obj_id)

        result = await self.collection.insert_one(obj_data)
        obj_data["id"] = str(result.inserted_id)
        obj_data.pop("_id", None)
        return obj_data

    async def update(self, id: str, obj_in: Any) -> Dict[str, Any] | None:
        """Update fields of an existing document."""
        if not ObjectId.is_valid(id):
            return None

        if not isinstance(obj_in, dict):
            update_data = obj_in.model_dump(exclude_unset=True)
        else:
            update_data = obj_in.copy()

        # Do not allow modifying id
        update_data.pop("id", None)
        update_data.pop("_id", None)

        result = await self.collection.find_one_and_update(
            {"_id": ObjectId(id)},
            {"$set": update_data},
            return_document=True
        )
        if result:
            result["id"] = str(result.pop("_id"))
            return result
        return None

    async def remove(self, id: str) -> bool:
        """Delete a document by stringified ObjectId."""
        if not ObjectId.is_valid(id):
            return False
        result = await self.collection.delete_one({"_id": ObjectId(id)})
        return result.deleted_count > 0
