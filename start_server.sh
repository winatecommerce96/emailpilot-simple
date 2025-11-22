#!/bin/bash
# EmailPilot Simple Server Startup Script

cd "$(dirname "$0")"

# Activate virtual environment
source .venv/bin/activate

# Set environment variables
export GOOGLE_CLOUD_PROJECT=emailpilot-438321

# Start the server
echo "Starting EmailPilot Simple API server on port 8001..."
echo "Press Ctrl+C to stop"
echo ""

uvicorn api:app --reload --port 8001 --host 0.0.0.0
