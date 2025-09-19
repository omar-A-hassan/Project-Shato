# Use Python 3.11 slim image
FROM python:3.11-slim

# Install system dependencies for audio processing
RUN apt-get update && apt-get install -y --no-install-recommends \
    portaudio19-dev \
    libasound2-dev \
    build-essential \
    python3-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements first (for better caching)
COPY requirements.txt .

# Upgrade pip and install Python dependencies with extended timeout and retry logic
RUN pip install --upgrade pip && \
    pip install --no-cache-dir --timeout=300 --retries=3 --trusted-host pypi.org --trusted-host pypi.python.org --trusted-host files.pythonhosted.org -r requirements.txt

# Copy application code
COPY app/ ./app/

# Create directories for audio files
RUN mkdir -p recordings tts_audio

# Set environment variables
ENV PYTHONPATH=/app

# Expose port
EXPOSE 7860

# Run the Gradio application
CMD ["python", "app/main.py"]