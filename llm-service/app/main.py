from fastapi import FastAPI, HTTPException
import logging
import json
from typing import Optional

from .models.model_runner_client import ModelRunnerClient
from .services.prompt_builder import PromptBuilder

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="LLM Service API",
    description="Generates conversational responses and robot commands using fine-tuned SHATO Gemma 270M",
    version="1.0.0"
)

# Initialize service components
model_client = ModelRunnerClient()
prompt_builder = PromptBuilder()

@app.on_event("startup")
async def startup_event():
    """Initialize model on startup."""
    logger.info("[LLM-SERVICE] Starting up...")
    is_healthy = await model_client.health_check()
    if is_healthy.get("model_runner_healthy", False):
        logger.info("[LLM-SERVICE] Docker Model Runner connection verified on startup")
    else:
        logger.warning("[LLM-SERVICE] Docker Model Runner not immediately available, will retry on requests")

@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown."""
    logger.info("[LLM-SERVICE] Shutting down...")
    logger.info("[LLM-SERVICE] Docker Model Runner will handle cleanup automatically")


@app.get("/")
async def health_check():
    """Health check endpoint to verify the service is running."""
    model_status = await model_client.health_check()
    
    return {
        "status": "healthy" if model_status.get("model_runner_healthy", False) else "degraded",
        "service": "llm-service",
        "model_status": model_status
    }


@app.get("/health")
async def simple_health():
    """Simple health endpoint for Docker health checks."""
    return {"status": "healthy"}


@app.post("/generate_response")
async def generate_response(request: dict):
    """
    Generate response using original single-pass approach with context-aware prompting.
    Supports optional retry_context for validation error recovery.
    """
    try:
        user_input = request.get("user_input", "")
        retry_context = request.get("retry_context")
        correlation_id = request.get("correlation_id", "unknown")
        
        if not user_input.strip():
            raise HTTPException(status_code=400, detail="user_input is required")
        
        if retry_context:
            logger.info("llm_retry_request", extra={
                "correlation_id": correlation_id,
                "user_input": user_input,
                "retry_context": retry_context,
                "service": "llm-service"
            })
        else:
            logger.info("llm_request_received", extra={
                "correlation_id": correlation_id,
                "user_input": user_input,
                "service": "llm-service"
            })
        
        # Check Model Runner health
        health_status = await model_client.health_check()
        if not health_status.get("model_runner_healthy", False):
            logger.error("[LLM-SERVICE-ERROR] Docker Model Runner not available")
            raise HTTPException(status_code=503, detail="Model not available")
        
        # Single pass: Generate response with context-appropriate examples and optional retry context
        result = await call_model_with_prompt(user_input, retry_context)
        
        # Parse the result to determine if it's a command or chat
        if "command" in result and result["command"]:
            logger.info("llm_command_generated", extra={
                "correlation_id": correlation_id,
                "command": result.get('command', 'unknown'),
                "response": result.get("response", ""),
                "service": "llm-service"
            })
            return build_command_response(
                result.get("response", "Command received"),
                result.get("command"),
                result.get("command_params", {})
            )
        else:
            logger.info("llm_chat_generated", extra={
                "correlation_id": correlation_id,
                "response": result.get("response", ""),
                "service": "llm-service"
            })
            return build_chat_response(result.get("response", "I'm ready to help!"))
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[LLM-SERVICE-ERROR] {str(e)}")
        return build_error_response("I encountered an error processing your request.")


# Helper functions using original prompt builder
async def call_model_with_prompt(user_input: str, retry_context: str = None) -> dict:
    """Call fine-tuned SHATO model with proper conversation format."""
    # Get clean system prompt that matches training format
    system_prompt = prompt_builder.build_prompt(user_input, retry_context)
    
    # Pass retry_context separately to be added to user message (matches training)
    response = await model_client.generate_response(user_input, system_prompt, retry_context)
    logger.info(f"[LLM-SERVICE] Model raw response: {repr(response)}")
    try:
        # Fine-tuned model returns pure JSON output
        return json.loads(response.strip())
    except json.JSONDecodeError as e:
        logger.error(f"[LLM-SERVICE] JSON parse error: {e}")
        # Fallback for chat
        return {"response": "I'm ready to help with robot commands!", "command": None, "command_params": None}

def build_chat_response(chat_text: str) -> dict:
    """Build response for chat interactions."""
    return {
        "response": chat_text,
        "command": None,
        "command_params": None
    }

def build_command_response(model_response: str, command_type: str, params: dict) -> dict:
    """Build response for robot commands."""
    return {
        "response": model_response,
        "command": command_type,
        "command_params": params
    }

def build_error_response(error_message: str) -> dict:
    """Build error response."""
    return {
        "response": error_message,
        "command": None,
        "command_params": None
    }


@app.get("/stats")
async def get_stats():
    """Get service statistics."""
    model_status = await model_client.health_check()
    return {
        "model_runner_status": model_status,
        "prompt_builder_loaded": prompt_builder.is_loaded(),
        "service": "llm-service",
        "version": "1.0.0"
    }


@app.post("/reload_model")
async def reload_model():
    """Check Docker Model Runner status (admin endpoint)."""
    model_status = await model_client.health_check()
    success = model_status.get("model_runner_healthy", False)
    return {
        "success": success,
        "message": "Docker Model Runner is healthy" if success else "Docker Model Runner not available",
        "model_status": model_status
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8002)