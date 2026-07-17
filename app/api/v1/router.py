from fastapi import APIRouter
from app.api.v1.endpoints import documents, health, items, versioned_docs, selections, generation

api_router = APIRouter()

# Register versioned_docs first so GET /documents lists SQL versioned documents
api_router.include_router(versioned_docs.router, tags=["Versioned Browsing & Search"])
api_router.include_router(health.router, prefix="/health", tags=["Health"])
api_router.include_router(items.router, prefix="/items", tags=["Items"])
api_router.include_router(documents.router, prefix="/documents", tags=["Documents"])
api_router.include_router(selections.router, tags=["Selections"])
api_router.include_router(generation.router, prefix="/generation", tags=["LLM Generation Retrieval"])
