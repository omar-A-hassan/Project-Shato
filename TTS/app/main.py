from fastapi import FastAPI, HTTPException
import logging
import base64
import io
import torch
from parler_tts import ParlerTTSForConditionalGeneration
from transformers import AutoTokenizer
import soundfile as sf
import numpy as np
import re
from num2words import num2words

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="SHATO TTS Service",
    description="Text-to-Speech service using Parler TTS for robot voice responses",
    version="1.0.0",
)

# Global model variables
model = None
tokenizer = None
device = None


# Normalize numbers to their word representation
def normalize_numbers(text: str, lang: str = "en") -> str:
    def replace_number(match):
        number = int(match.group())
        return num2words(number, lang=lang)

    return re.sub(r"\d+", replace_number, text)


def clean_text_for_tts(text: str) -> str:
    """
    Clean text for TTS by removing punctuation and non-alphanumeric characters.
    Keeps only letters, numbers, and spaces.
    """
    # Remove all characters that are not letters, numbers, or spaces
    cleaned = re.sub(r"[^a-zA-Z0-9\s]", "", text)
    # Replace multiple spaces with single space
    cleaned = re.sub(r"\s+", " ", cleaned)
    # Replace capital letters with lowercase
    cleaned = cleaned.lower()
    # Normalize numbers
    cleaned = normalize_numbers(cleaned)
    # Strip leading/trailing whitespace
    return cleaned.strip()


@app.on_event("startup")
async def startup_event():
    """Initialize TTS model on startup."""
    global model, tokenizer, device

    logger.info("[TTS-SERVICE] Starting up...")

    try:
        # Device selection: CUDA > MPS > CPU
        if torch.cuda.is_available():
            device = "cuda:0"
        elif torch.backends.mps.is_available():
            device = "mps"
        else:
            device = "cpu"
        logger.info(f"[TTS-SERVICE] Using device: {device}")

        model_path = "parler-tts/parler-tts-tiny-v1"
        logger.info(f"[TTS-SERVICE] Loading model: {model_path}")

        model = ParlerTTSForConditionalGeneration.from_pretrained(model_path).to(device)
        tokenizer = AutoTokenizer.from_pretrained(model_path)

        logger.info("[TTS-SERVICE] Model loaded successfully")

    except Exception as e:
        logger.error(f"[TTS-SERVICE-ERROR] Failed to load model: {str(e)}")
        raise


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown."""
    logger.info("[TTS-SERVICE] Shutting down...")


@app.get("/")
async def health_check():
    """Health check endpoint to verify the service is running."""
    return {
        "status": "healthy" if model is not None else "degraded",
        "service": "tts-service",
        "model_loaded": model is not None,
        "device": str(device) if device else "unknown",
    }


@app.get("/health")
async def simple_health():
    """Simple health endpoint for Docker health checks."""
    return {"status": "healthy"}


@app.post("/synthesize")
async def synthesize_speech(request: dict):
    """
    Convert text to speech using Parler TTS.

    Request format:
    {
        "text": "Hello, I'm moving to position 5, 7",
        "correlation_id": "12345678",
        "voice_description": "optional custom voice description"
    }

    Response format:
    {
        "audio_data": "base64_encoded_wav_audio",
        "correlation_id": "12345678",
        "duration_ms": 2500,
        "sample_rate": 24000
    }
    """
    try:
        text = clean_text_for_tts(request.get("text", ""))
        correlation_id = request.get("correlation_id", "unknown")
        voice_description = request.get(
            "voice_description",
            "Jon's voice is monotone yet slightly fast in delivery, with a very close recording that almost has no background noise."
            "The recording is of very high quality, with the speaker's voice sounding clear and professional.",
        )

        if not text.strip():
            raise HTTPException(status_code=400, detail="text is required")

        logger.info(
            "tts_request_received",
            extra={
                "correlation_id": correlation_id,
                "text": text[:100] + "..." if len(text) > 100 else text,
                "service": "tts-service",
            },
        )

        # Check if model is loaded
        if model is None or tokenizer is None:
            logger.error("[TTS-SERVICE-ERROR] Model not loaded")
            raise HTTPException(status_code=503, detail="TTS model not available")

        # Tokenize description and text
        desc_inputs = tokenizer(voice_description, return_tensors="pt", padding=True)
        prompt_inputs = tokenizer(text, return_tensors="pt", padding=True)

        # Move to device
        input_ids = desc_inputs.input_ids.to(device)
        attention_mask = desc_inputs.attention_mask.to(device)
        prompt_input_ids = prompt_inputs.input_ids.to(device)
        prompt_attention_mask = prompt_inputs.attention_mask.to(device)

        # Generate audio
        logger.info(
            f"[TTS-SERVICE] Generating audio for correlation_id={correlation_id}"
        )

        with torch.no_grad():
            generation = model.generate(
                input_ids=input_ids,
                attention_mask=attention_mask,
                prompt_input_ids=prompt_input_ids,
                prompt_attention_mask=prompt_attention_mask,
                max_length=10000,  # Increased for longer text
                min_length=100,  # Increased minimum to ensure complete sentences
                do_sample=True,
                temperature=0.8,  # Slightly higher for more natural speech
            )

        # Convert to numpy array
        audio_arr = generation.cpu().numpy().squeeze()
        sample_rate = model.config.sampling_rate

        # Convert audio to base64 encoded WAV
        audio_buffer = io.BytesIO()
        sf.write(audio_buffer, audio_arr, sample_rate, format="WAV")
        audio_buffer.seek(0)
        audio_base64 = base64.b64encode(audio_buffer.getvalue()).decode("utf-8")

        # Calculate duration
        duration_ms = int((len(audio_arr) / sample_rate) * 1000)

        logger.info(
            "tts_audio_generated",
            extra={
                "correlation_id": correlation_id,
                "duration_ms": duration_ms,
                "sample_rate": sample_rate,
                "service": "tts-service",
            },
        )

        return {
            "audio_data": audio_base64,
            "correlation_id": correlation_id,
            "duration_ms": duration_ms,
            "sample_rate": sample_rate,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[TTS-SERVICE-ERROR] {str(e)}")
        raise HTTPException(status_code=500, detail=f"TTS generation failed: {str(e)}")


@app.get("/stats")
async def get_stats():
    """Get service statistics."""
    return {
        "model_loaded": model is not None,
        "device": str(device) if device else "unknown",
        "service": "tts-service",
        "version": "1.0.0",
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8004)
