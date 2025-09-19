# Use Python 3.11 slim image
FROM python:3.11-slim

# Install system dependencies for audio processing
RUN apt-get update && apt-get install -y --no-install-recommends \
    libsndfile1 \
    libgomp1 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements first (for better caching)
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY app/ ./app/

# Pre-download Parler TTS model during build to avoid runtime downloads
RUN python -c "from transformers import AutoTokenizer; from parler_tts import ParlerTTSForConditionalGeneration; model_path='parler-tts/parler-tts-tiny-v1'; ParlerTTSForConditionalGeneration.from_pretrained(model_path); AutoTokenizer.from_pretrained(model_path)"

# Set environment variables
ENV PYTHONPATH=/app

# Expose port
EXPOSE 8004

# Run the FastAPI application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8004"]
