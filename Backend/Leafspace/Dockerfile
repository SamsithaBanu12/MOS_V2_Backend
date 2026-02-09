FROM python:3.10-slim

WORKDIR /app

# Install system dependencies if any (none apparent from code, but good practice to have basics)
# RUN apt-get update && apt-get install -y --no-install-recommends ...

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Expose the specific port
EXPOSE 8020

# Run the application
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8020"]
