from typing import List
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db_session
from app.schemas.generation_retrieval import GenerationRetrievalResponse
from app.services import generation_retrieval

router = APIRouter()


@router.get("/{selection_id}", response_model=GenerationRetrievalResponse)
async def get_generation_by_selection(
    selection_id: int,
    db: AsyncSession = Depends(get_db_session)
):
    """
    Retrieve successfully generated test cases, version info, staleness status,
    and a diff summary for a specific Selection ID.
    """
    return await generation_retrieval.get_generation_by_selection_id(selection_id, db)


@router.get("/node/{node_id}", response_model=List[GenerationRetrievalResponse])
async def get_generations_by_node(
    node_id: str,
    db: AsyncSession = Depends(get_db_session)
):
    """
    Retrieve successfully generated test cases, version info, staleness status,
    and a diff summary for any selections containing the given Node (ID or UUID).
    """
    return await generation_retrieval.get_generations_by_node_id(node_id, db)
