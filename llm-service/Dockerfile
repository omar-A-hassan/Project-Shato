# Use Python 3.11 slim image for FastAPI service
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first (for better Docker layer caching)
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY app/ ./app/
COPY prompts/ ./prompts/

# Set environment variables
ENV PYTHONPATH=/app

# Expose port 8002 (LLM service port)
EXPOSE 8002

# Run the LLM service
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8002"]