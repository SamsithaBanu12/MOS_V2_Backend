#!/usr/bin/env bash
set -e

echo "[ENTRYPOINT] Starting ws_ingestor and health_consumer..."

# Start ws_ingestor in background
python -m netra_backend.services.ws_ingestor &
WS_PID=$!

# Start health_consumer in background
python -m netra_backend.services.health_consumer &
HC_PID=$!

# Wait for any one of them to exit
wait -n $WS_PID $HC_PID
EXIT_CODE=$?

echo "[ENTRYPOINT] One of the services exited with code $EXIT_CODE. Exiting container."
exit $EXIT_CODE
