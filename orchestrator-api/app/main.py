from fastapi import FastAPI, UploadFile, File, HTTPException
import httpx
import logging
import os
import uuid
import time

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="SHATO Orchestrator",
    description="Simple routing between LLM and validator services",
    version="1.0.0"
)

# Service URLs from environment variables with fallback defaults
LLM_URL = os.getenv("LLM_SERVICE_URL", "http://llm-service:8002")
VALIDATOR_URL = os.getenv("VALIDATOR_SERVICE_URL", "http://robot-validator:8000")
STT_URL = os.getenv("STT_SERVICE_URL", "http://stt-service:8003")

# Log configuration on startup
logger.info(f"[ORCHESTRATOR] LLM Service URL: {LLM_URL}")
logger.info(f"[ORCHESTRATOR] Validator Service URL: {VALIDATOR_URL}")
logger.info(f"[ORCHESTRATOR] STT Service URL: {STT_URL}")


@app.get("/health")
async def health():
    """Simple health check."""
    return {"status": "healthy"}


@app.post("/process")
async def process(request: dict):
    """
    Main routing logic: LLM -> Validator (if command) -> Response
    """
    # Use UI correlation ID or generate new one if not provided
    correlation_id = request.get("correlation_id") or str(uuid.uuid4())[:8]
    start_time = time.time()
    user_input = request.get("user_input", "")
    
    # Log request received with correlation ID
    logger.info("request_received", extra={
        "correlation_id": correlation_id,
        "user_input": user_input,
        "service": "orchestrator"
    })
    
    # Step 1: Call LLM service
    logger.info(f"[ORCHESTRATOR] calling_llm_service correlation_id={correlation_id}")
    
    async with httpx.AsyncClient(timeout=120.0) as client:
        llm_response = await client.post(
            f"{LLM_URL}/generate_response",
            json={"user_input": user_input, "correlation_id": correlation_id}
        )
        llm_data = llm_response.json()
    
    # Step 2: Simple routing decision
    if llm_data.get("command") is not None:
        # COMMAND PATH: Send to validator
        logger.info(f"[ORCHESTRATOR] command_detected correlation_id={correlation_id} command={llm_data['command']}")
        
        logger.info(f"[ORCHESTRATOR] calling_validator correlation_id={correlation_id} command={llm_data['command']}")
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            validator_response = await client.post(
                f"{VALIDATOR_URL}/execute_command",
                json={
                    "command": llm_data["command"],
                    "command_params": llm_data["command_params"],
                    "correlation_id": correlation_id
                }
            )
            validator_data = validator_response.json()
        
        if not validator_data.get("success", False):
            # Validation failed - retry with error context
            logger.info("validation_failed_retrying", extra={
                "correlation_id": correlation_id,
                "error": validator_data.get("error", "Validation failed"),
                "service": "orchestrator"
            })
            
            async with httpx.AsyncClient(timeout=120.0) as client:
                retry_response = await client.post(
                    f"{LLM_URL}/generate_response",
                    json={
                        "user_input": user_input,
                        "retry_context": validator_data.get("error", "Validation failed"),
                        "correlation_id": correlation_id
                    }
                )
                llm_data = retry_response.json()
        
        # Log successful completion
        duration_ms = int((time.time() - start_time) * 1000)
        logger.info(f"[ORCHESTRATOR] request_completed correlation_id={correlation_id} status=success duration_ms={duration_ms} command={llm_data.get('command')}")
        
        # Return LLM response with validation info
        return {
            **llm_data,
            "validation_result": validator_data.get("message") if validator_data.get("success") else None
        }
    else:
        # CHAT PATH: Return LLM response directly
        duration_ms = int((time.time() - start_time) * 1000)
        logger.info("chat_response_completed", extra={
            "correlation_id": correlation_id,
            "status": "success",
            "duration_ms": duration_ms,
            "service": "orchestrator"
        })
        return llm_data


@app.post("/process_voice")
async def process_voice(audio_file: UploadFile = File(...), correlation_id: str = None):
    """
    Voice processing pipeline: STT -> LLM -> Validator (if command) -> Response
    """
    # Generate correlation ID if not provided
    correlation_id = correlation_id or str(uuid.uuid4())[:8]
    start_time = time.time()

    # Log voice request received
    logger.info("voice_request_received", extra={
        "correlation_id": correlation_id,
        "audio_filename": audio_file.filename,
        "content_type": audio_file.content_type,
        "service": "orchestrator"
    })

    try:
        # Step 1: Send audio to STT service
        logger.info(f"[ORCHESTRATOR] calling_stt_service correlation_id={correlation_id}")

        # Read audio file content
        audio_content = await audio_file.read()

        # Create form data for STT service
        files = {"audio_file": (audio_file.filename, audio_content, audio_file.content_type)}
        data = {"correlation_id": correlation_id}

        async with httpx.AsyncClient(timeout=60.0) as client:
            stt_response = await client.post(
                f"{STT_URL}/transcribe",
                files=files,
                data=data
            )

            if stt_response.status_code != 200:
                raise HTTPException(status_code=500, detail=f"STT service error: {stt_response.status_code}")

            stt_data = stt_response.json()
            transcribed_text = stt_data.get("text", "").strip()

            if not transcribed_text:
                raise HTTPException(status_code=400, detail="No text transcribed from audio")

        logger.info(f"[ORCHESTRATOR] stt_completed correlation_id={correlation_id} text='{transcribed_text}'")

        # Step 2: Process transcribed text through existing pipeline
        text_request = {
            "user_input": transcribed_text,
            "correlation_id": correlation_id
        }

        # Call existing process function logic
        result = await process(text_request)

        # Add STT info to response
        result["transcribed_text"] = transcribed_text
        result["original_filename"] = audio_file.filename

        # Log completion
        duration_ms = int((time.time() - start_time) * 1000)
        logger.info("voice_request_completed", extra={
            "correlation_id": correlation_id,
            "status": "success",
            "duration_ms": duration_ms,
            "transcribed_text": transcribed_text,
            "service": "orchestrator"
        })

        return result

    except HTTPException:
        raise
    except Exception as e:
        duration_ms = int((time.time() - start_time) * 1000)
        logger.error("voice_request_failed", extra={
            "correlation_id": correlation_id,
            "error": str(e),
            "duration_ms": duration_ms,
            "service": "orchestrator"
        })
        raise HTTPException(status_code=500, detail=f"Voice processing failed: {str(e)}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)