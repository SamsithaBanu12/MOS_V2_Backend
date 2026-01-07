# Use a slim Python base image
FROM python:3.12-slim

# Install system dependencies needed for psycopg2 (Postgres driver)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
 && rm -rf /var/lib/apt/lists/*

# Set work directory
WORKDIR /app

# Copy requirements first (for better caching)
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy your backend code into the image
COPY netra_backend ./netra_backend
COPY entrypoint.sh .

# Make sure entrypoint script is executable and has LF line endings
RUN apt-get update && apt-get install -y dos2unix && rm -rf /var/lib/apt/lists/*
RUN dos2unix entrypoint.sh && chmod +x entrypoint.sh

# Default command: run both services
CMD ["./entrypoint.sh"]
