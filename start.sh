#!/bin/bash
# Cloud B1 Simplifier - Start script (Linux/macOS)
set -e

cd "$(dirname "$0")"

# Check virtualenv
if [ ! -d "venv" ]; then
    echo "Error: Virtual environment not found"
    echo "Create it: python3 -m venv venv && venv/bin/pip install -r requirements.txt"
    exit 1
fi

# Check if already running (try curl on localhost)
PORT="${SIMPLIFIER_PORT:-8890}"
if curl -s --max-time 2 "http://localhost:$PORT/health" > /dev/null 2>&1; then
    echo "Server already running on port $PORT"
    echo "Opening browser..."
    xdg-open "http://localhost:$PORT" 2>/dev/null || open "http://localhost:$PORT" 2>/dev/null || true
    exit 0
fi

echo "Starting server on http://localhost:$PORT"
echo "Press Ctrl+C to stop"
echo ""

# Open browser in background
(sleep 2 && (xdg-open "http://localhost:$PORT" 2>/dev/null || open "http://localhost:$PORT" 2>/dev/null || true)) &

# Run server
venv/bin/python -m src.main
