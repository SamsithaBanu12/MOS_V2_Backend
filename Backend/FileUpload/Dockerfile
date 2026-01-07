# Final Environment
FROM python:3.12-slim

WORKDIR /app

# Install runtime dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy Python Code
COPY main.py new_connector.py entrypoint.sh ./

# Copy C files (optional - may not compile if lib is missing)
COPY upload_image.c file_transfer.h ./

# Copy lib directory
COPY lib/ ./lib/

# Set library path and compile C code (if lib exists)
RUN if [ -d "./lib" ]; then \
      gcc -pthread upload_image.c -o upload_image -L./lib -lftm_gs && \
      chmod +x upload_image; \
    fi

ENV LD_LIBRARY_PATH=/app/lib:$LD_LIBRARY_PATH

# Install Python Deps
RUN pip install --no-cache-dir fastapi uvicorn python-multipart requests

# Permissions
RUN chmod +x entrypoint.sh

# Create uploads directory
RUN mkdir -p /app/uploads

# Expose API port
EXPOSE 8080

# Entrypoint
ENTRYPOINT ["./entrypoint.sh"]
