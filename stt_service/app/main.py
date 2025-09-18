from fastapi import FastAPI, UploadFile, File, Form, HTTPException
import whisper
import tempfile
import os
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="SHATO STT Service",
    description="Speech-to-Text service using OpenAI Whisper",
    version="1.0.0"
)

# Load Whisper model on startup
model = whisper.load_model("base")

@app.get("/health")
async def health():
    """Health check endpoint"""
    return {"status": "healthy"}

@app.post("/transcribe")
async def transcribe(audio_file: UploadFile = File(...), correlation_id: str = Form("unknown")):
    """
    Transcribe uploaded audio file to text
    """
    try:
        logger.info(f"[STT-SERVICE] transcription_request correlation_id={correlation_id} filename={audio_file.filename}")

        # Save uploaded file to temporary location
        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as temp_file:
            content = await audio_file.read()
            temp_file.write(content)
            temp_file_path = temp_file.name

        # Transcribe using Whisper
        result = model.transcribe(temp_file_path, language="en")
        transcribed_text = result["text"].strip()

        # Clean up temporary file
        os.unlink(temp_file_path)

        logger.info(f"[STT-SERVICE] transcription_completed correlation_id={correlation_id} text='{transcribed_text}'")

        return {
            "text": transcribed_text,
            "correlation_id": correlation_id,
            "language": "en",
            "status": "success"
        }

    except Exception as e:
        logger.error(f"[STT-SERVICE] transcription_failed correlation_id={correlation_id} error={str(e)}")
        raise HTTPException(status_code=500, detail=f"Transcription failed: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8003)