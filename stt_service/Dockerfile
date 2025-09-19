FROM python:3.11-slim

# Install system dependencies for audio processing
RUN apt-get update && apt-get install -y \
    libsndfile1 \
    ffmpeg \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir pip setuptools wheel \
    && pip install --no-cache-dir -r requirements.txt

COPY app/ ./app/

# Pre-download Whisper model during build to avoid runtime downloads
RUN python -c "import whisper; whisper.load_model('base')"

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8003"]