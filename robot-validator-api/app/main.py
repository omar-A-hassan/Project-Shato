from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
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
        # Extract command and parameters from request
        command = request.command
        command_params = request.command_params
        
        logger.info(f"[ROBOT-VALIDATOR] Received command request: {command} with params {command_params}")
        
        # Validate the command
        is_valid, success_response, error_response = validator.validate_command(
            command, command_params
        )
        
        if is_valid:
            # Command is valid - simulate robot action
            simulation_result = simulate_robot_action(command, command_params)
            
            # Add simulation result to success response
            success_response.message = f"{success_response.message}. {simulation_result}"
            
            return success_response
        else:
            # Command is invalid - return error
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