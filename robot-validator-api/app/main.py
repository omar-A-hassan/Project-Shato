from fastapi import FastAPI, HTTPException
import logging

from .schemas.api_schemas import CommandRequest, CommandValidationResponse
from .validators.command_validator import RobotCommandValidator, simulate_robot_action
from .models.responses import HealthCheckResponse

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="Robot Validator API",
    description="Validates robot commands against strict schema and simulates robot actions",
    version="1.0.0"
)

# Initialize validator
validator = RobotCommandValidator()


@app.get("/", response_model=HealthCheckResponse)
async def health_check():
    """Health check endpoint to verify the service is running."""
    return HealthCheckResponse()


@app.post("/execute_command", response_model=CommandValidationResponse)
async def execute_command(request: CommandRequest):
    """
    Validate and execute a robot command.
    
    This endpoint:
    1. Validates the incoming command against strict schema
    2. Logs validation results
    3. If valid, simulates the robot action
    4. Returns appropriate success or error response
    """
    try:
        # Extract command, parameters, and correlation ID from request
        command = request.command
        command_params = request.command_params
        correlation_id = getattr(request, 'correlation_id', 'unknown') or 'unknown'
        
        logger.info("validator_request_received", extra={
            "correlation_id": correlation_id,
            "command": command,
            "command_params": command_params,
            "service": "validator"
        })
        
        # Validate the command
        is_valid, success_response, error_response = validator.validate_command(
            command, command_params
        )
        
        if is_valid:
            # Command is valid - simulate robot action
            logger.info("validation_success", extra={
                "correlation_id": correlation_id,
                "command": command,
                "service": "validator"
            })
            
            simulation_result = simulate_robot_action(command, command_params)
            
            # Add simulation result to success response
            success_response.message = f"{success_response.message}. {simulation_result}"
            
            logger.info("command_executed", extra={
                "correlation_id": correlation_id,
                "command": command,
                "simulation_result": simulation_result,
                "service": "validator"
            })
            
            return success_response
        else:
            # Command is invalid - return error
            logger.info("validation_failed", extra={
                "correlation_id": correlation_id,
                "command": command,
                "error": error_response.error,
                "service": "validator"
            })
            return error_response
            
    except Exception as e:
        # Handle unexpected errors
        error_msg = f"Unexpected error processing command: {str(e)}"
        logger.error(f"[ROBOT-VALIDATOR-ERROR] {error_msg}")
        
        raise HTTPException(
            status_code=500,
            detail={
                "success": False,
                "error": error_msg,
                "details": "Internal server error"
            }
        )


@app.get("/health")
async def simple_health():
    """Simple health endpoint for Docker health checks."""
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)