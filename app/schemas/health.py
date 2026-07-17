from pydantic import BaseModel


class HealthCheckResponse(BaseModel):
    """Pydantic schema representing the health check response status."""
    status: str
    message: str
