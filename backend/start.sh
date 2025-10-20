#!/bin/bash

# Start script for FastAPI backend

echo "Starting FastAPI backend..."

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate

# Install dependencies
echo "Installing dependencies..."
pip install -r requirements.txt

# Start the server
echo "Starting server on http://localhost:8000..."
uvicorn main:app --reload --host 0.0.0.0 --port 8000
