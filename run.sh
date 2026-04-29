#!/bin/bash
echo "Starting application..."

# Check if python3 is available
if command -v python3 &> /dev/null; then
    PYTHON_CMD="python3"
elif command -v python &> /dev/null; then
    PYTHON_CMD="python"
else
    echo "Error: Python is not installed or not in PATH."
    echo "Please install Python and try again."
    exit 1
fi

# Run the main script
$PYTHON_CMD main.py