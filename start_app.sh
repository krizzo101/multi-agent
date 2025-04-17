#!/bin/bash

# Load environment variables
source .env 2>/dev/null || echo "No .env file found, using defaults"

# Default values if not in environment
API_HOST=${API_HOST:-"0.0.0.0"}
API_PORT=${API_PORT:-"8000"}
UI_PORT=${UI_PORT:-"8501"}
UI_ADDRESS=${UI_ADDRESS:-"0.0.0.0"}

# Setup virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
    source venv/bin/activate
    pip install -r requirements.txt
else
    source venv/bin/activate
fi

# Function to check if a command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Check if the required commands exist
if ! command_exists uvicorn || ! command_exists streamlit; then
    echo "Installing required packages..."
    pip install -r requirements.txt
fi

# Function to stop all processes on script exit
cleanup() {
    echo "Stopping services..."
    kill $API_PID $UI_PID 2>/dev/null
    exit 0
}

# Register the cleanup function for when the script is terminated
trap cleanup SIGINT SIGTERM

# Start FastAPI backend
echo "Starting FastAPI backend on http://$API_HOST:$API_PORT..."
uvicorn app_fastapi:app --host $API_HOST --port $API_PORT --reload &
API_PID=$!

# Start Streamlit frontend
echo "Starting Streamlit frontend on http://$UI_ADDRESS:$UI_PORT..."
streamlit run app_streamlit.py --server.port=$UI_PORT --server.address=$UI_ADDRESS &
UI_PID=$!

echo "Both services are now running!"
echo "FastAPI: http://$API_HOST:$API_PORT"
echo "Streamlit: http://$UI_ADDRESS:$UI_PORT"
echo "Press Ctrl+C to stop all services."

# Wait for either process to exit
wait $API_PID $UI_PID 