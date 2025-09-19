import logging
from typing import Dict, Any, Tuple, Optional
from pydantic import ValidationError

from ..models.commands import MoveToCommand, RotateCommand, StartPatrolCommand
from ..models.responses import ValidationSuccessResponse, ValidationErrorResponse


# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class RobotCommandValidator:
    """Validates robot commands against strict schema requirements."""
    
    def __init__(self):
        # Map command names to their corresponding Pydantic models
        self.command_models = {
            "move_to": MoveToCommand,
            "rotate": RotateCommand,
            "start_patrol": StartPatrolCommand
        }
    
    def validate_command(self, command: str, command_params: Dict[str, Any]) -> Tuple[bool, Optional[ValidationSuccessResponse], Optional[ValidationErrorResponse]]:
        """
        Validate a robot command against the strict schema.
        
        Args:
            command: Command name (e.g., "move_to")
            command_params: Dictionary of command parameters
            
        Returns:
            Tuple of (is_valid, success_response, error_response)
        """
        # Check if command name is valid
        if command not in self.command_models:
            error_msg = f"Invalid command. Reason: Unknown command name '{command}'"
            logger.error(f"[ROBOT-VALIDATOR-ERROR] {error_msg}")
            
            return False, None, ValidationErrorResponse(
                error=error_msg,
                details=f"Valid commands are: {', '.join(self.command_models.keys())}"
            )
        
        # Try to validate with the appropriate Pydantic model
        try:
            command_data = {
                "command": command,
                "command_params": command_params
            }
            
            # Validate using the specific command model
            validated_command = self.command_models[command](**command_data)
            
            # Log success
            success_msg = f"Received and validated command: '{command}' with params {command_params}"
            logger.info(f"[ROBOT-VALIDATOR-SUCCESS] {success_msg}")
            
            return True, ValidationSuccessResponse(
                message=success_msg,
                command=command,
                command_params=command_params
            ), None
            
        except ValidationError as e:
            # Parse Pydantic validation errors to create detailed error messages
            error_details = self._parse_validation_error(command, e)
            error_msg = f"Invalid params for '{command}': {error_details}"
            
            logger.error(f"[ROBOT-VALIDATOR-ERROR] {error_msg}")
            
            return False, None, ValidationErrorResponse(
                error=error_msg,
                details=str(e)
            )
    
    def _parse_validation_error(self, command: str, error: ValidationError) -> str:
        """
        Parse Pydantic validation error into human-readable message.
        
        Args:
            command: The command that failed validation
            error: Pydantic ValidationError
            
        Returns:
            Human-readable error description
        """
        errors = error.errors()
        
        if not errors:
            return "Unknown validation error"
        
        # Get the first error for simplicity
        first_error = errors[0]
        error_type = first_error.get('type', '')
        field_path = ' -> '.join(str(loc) for loc in first_error.get('loc', []))
        
        # Handle common error types with specific messages
        if error_type == 'missing':
            return f"Missing required key '{field_path.split(' -> ')[-1]}'"
        elif error_type == 'literal_error':
            expected = first_error.get('ctx', {}).get('expected', 'unknown')
            return f"Invalid value for '{field_path}'. Expected one of: {expected}"
        elif error_type == 'type_error':
            expected_type = first_error.get('msg', '').replace('Input should be ', '')
            return f"Wrong data type for '{field_path}'. {expected_type}"
        else:
            return first_error.get('msg', 'Validation error')


def simulate_robot_action(command: str, command_params: Dict[str, Any]) -> str:
    """
    Simulate the robot executing the validated command.
    This function simulates what the robot would do and returns a status message.
    
    Args:
        command: The validated command name
        command_params: The validated command parameters
        
    Returns:
        A string describing the simulated robot action
    """
    if command == "move_to":
        x = command_params["x"]
        y = command_params["y"]
        simulation_msg = f"SIMULATION: Robot navigating to coordinates ({x}, {y})"
        logger.info(f"[ROBOT-SIMULATOR] {simulation_msg}")
        return simulation_msg
        
    elif command == "rotate":
        angle = command_params["angle"]
        direction = command_params["direction"]
        simulation_msg = f"SIMULATION: Robot rotating {angle} degrees {direction}"
        logger.info(f"[ROBOT-SIMULATOR] {simulation_msg}")
        return simulation_msg
        
    elif command == "start_patrol":
        route_id = command_params["route_id"]
        speed = command_params.get("speed", "medium")
        repeat_count = command_params.get("repeat_count", 1)
        
        if repeat_count == -1:
            repeat_msg = "continuous patrol"
        else:
            repeat_msg = f"{repeat_count} time(s)"
            
        simulation_msg = f"SIMULATION: Robot starting {route_id} patrol at {speed} speed, repeating {repeat_msg}"
        logger.info(f"[ROBOT-SIMULATOR] {simulation_msg}")
        return simulation_msg
        
    else:
        # This shouldn't happen if validation worked correctly
        error_msg = f"Unknown command in simulation: {command}"
        logger.error(f"[ROBOT-SIMULATOR-ERROR] {error_msg}")
        return error_msg