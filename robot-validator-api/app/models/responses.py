from pydantic import BaseModel
from typing import Optional


class ValidationSuccessResponse(BaseModel):
    """Response model for successful command validation."""
    success: bool = True
    message: str
    command: str
    command_params: dict


class ValidationErrorResponse(BaseModel):
    """Response model for failed command validation."""
    success: bool = False
    error: str
    details: Optional[str] = None


class HealthCheckResponse(BaseModel):
    """Response model for health check endpoint."""
    status: str = "healthy"
    service: str = "robot-validator-api"