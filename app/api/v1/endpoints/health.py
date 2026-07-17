from fastapi import APIRouter
from app.schemas.health import HealthCheckResponse

router = APIRouter()


@router.get("", response_model=HealthCheckResponse)
async def check_health() -> HealthCheckResponse:
    """
    Simple API health check endpoint.
    Verifies that the application routing is active.
    """
    return HealthCheckResponse(status="healthy", message="Tri9T Backend API is operational.")
