from pydantic import BaseModel, Field
from typing import Dict, Any, Union, Optional
from ..models.responses import ValidationSuccessResponse, ValidationErrorResponse


class CommandRequest(BaseModel):
    """Schema for incoming command requests to /execute_command endpoint."""
    command: str = Field(..., description="Command name")
    command_params: Dict[str, Any] = Field(..., description="Command parameters")
    correlation_id: Optional[str] = Field(None, description="Request correlation ID for tracking")


# Union type for API responses
CommandValidationResponse = Union[ValidationSuccessResponse, ValidationErrorResponse]