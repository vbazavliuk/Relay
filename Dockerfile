FROM python:3.12-slim-bookworm@sha256:935c3c5b12357a7e10caa9e1c6ca5692344d97cf229832ef584be2cec9fc03df

# Prevent Python from buffering stdout/stderr and writing .pyc files
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# Install system dependencies: ffmpeg for media processing and ca-certificates for TLS
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user for security
RUN groupadd -r appuser && useradd -r -g appuser -u 1000 -d /app appuser \
    && chown -R appuser:appuser /app

# Install Python dependencies
COPY requirements.txt .
RUN pip install --require-hashes -r requirements.txt

# Copy application source code
COPY --chown=appuser:appuser . .

# Switch to non-root user
USER appuser

CMD ["python", "bot.py"]
