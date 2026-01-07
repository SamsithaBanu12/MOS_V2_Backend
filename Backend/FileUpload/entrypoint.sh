#!/bin/bash

# Start the Connector Bridge in the background
echo "Starting Connector Bridge..."
python new_connector.py &

# Start the FastAPI Backend
echo "Starting FastAPI Backend..."
uvicorn main:app --host 0.0.0.0 --port 8080
