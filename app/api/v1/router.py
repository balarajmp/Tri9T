from fastapi import APIRouter
from app.api.v1.endpoints import documents, health, items

api_router = APIRouter()

api_router.include_router(health.router, prefix="/health", tags=["Health"])
api_router.include_router(items.router, prefix="/items", tags=["Items"])
api_router.include_router(documents.router, prefix="/documents", tags=["Documents"])
