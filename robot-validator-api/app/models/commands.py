from typing import Literal, Optional
from pydantic import BaseModel, Field


class MoveToCommandParams(BaseModel):
    """Parameters for the move_to command."""
    x: float = Field(..., description="X coordinate")
    y: float = Field(..., description="Y coordinate")


class RotateCommandParams(BaseModel):
    """Parameters for the rotate command."""
    angle: float = Field(..., description="Rotation angle in degrees")
    direction: Literal["clockwise", "counter-clockwise"] = Field(
        ..., description="Direction of rotation"
    )


class StartPatrolCommandParams(BaseModel):
    """Parameters for the start_patrol command."""
    route_id: Literal["first_floor", "bedrooms", "second_floor"] = Field(
        ..., description="Route identifier"
    )
    speed: Literal["slow", "medium", "fast"] = Field(
        default="medium", description="Patrol speed"
    )
    repeat_count: int = Field(
        default=1, 
        ge=-1,  # Greater than or equal to -1
        description="Number of patrol loops. -1 for continuous, >= 1 for finite loops"
    )


class RobotCommand(BaseModel):
    """Base structure for all robot commands."""
    command: Literal["move_to", "rotate", "start_patrol"] = Field(
        ..., description="Command name"
    )
    command_params: dict = Field(..., description="Command parameters")


# Specific command models for validation
class MoveToCommand(BaseModel):
    """Complete move_to command with validation."""
    command: Literal["move_to"]
    command_params: MoveToCommandParams


class RotateCommand(BaseModel):
    """Complete rotate command with validation."""
    command: Literal["rotate"]
    command_params: RotateCommandParams


class StartPatrolCommand(BaseModel):
    """Complete start_patrol command with validation."""
    command: Literal["start_patrol"]
    command_params: StartPatrolCommandParams