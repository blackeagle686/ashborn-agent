#!/bin/bash
# start_server.sh
# Starts the Ashborn FastAPI backend server.

set -e

# Change to the directory of this script
cd "$(dirname "$0")"

echo "🔥 Starting Ashborn Backend Server..."

# Check if venv exists
if [ ! -d "venv" ]; then
    echo "❌ Error: Virtual environment 'venv' not found."
    echo "Please create it and install dependencies first."
    exit 1
fi

# Activate venv
source venv/bin/activate

# Start server
python3 -m uvicorn ashborn.server:app --host 127.0.0.1 --port 8765
