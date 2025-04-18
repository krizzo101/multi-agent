#!/bin/bash

# Load environment variables
source .env 2>/dev/null || echo "No .env file found, using defaults"

# Default values if not in environment
API_HOST=${API_HOST:-"0.0.0.0"}
API_PORT=${API_PORT:-"8000"}
UI_PORT=${UI_PORT:-"8501"}
UI_ADDRESS=${UI_ADDRESS:-"0.0.0.0"}

# Check if tracing is enabled
TRACING_ENABLED=false
if [ ! -z "$OPENAI_TRACE_LEVEL" ] && [ ! -z "$OPENAI_TRACE_DIR" ]; then
    TRACING_ENABLED=true
    echo "OpenAI Agents SDK tracing is enabled (level: $OPENAI_TRACE_LEVEL)"
    echo "Traces will be saved to: $OPENAI_TRACE_DIR"
fi

# Kill any running FastAPI and Streamlit processes
echo "Stopping any existing instances..."
pkill -f "uvicorn app_fastapi:app" || true
pkill -f "streamlit run app_streamlit.py" || true

# Make sure we terminate all FastAPI processes using port 8000
if command -v nc >/dev/null 2>&1; then
    if nc -z localhost $API_PORT 2>/dev/null; then
        echo "Port $API_PORT is still in use, finding and killing process..."
        if command -v lsof >/dev/null 2>&1; then
            PID=$(lsof -t -i:$API_PORT 2>/dev/null)
        elif command -v ss >/dev/null 2>&1; then
            PID=$(ss -lptn "sport = :$API_PORT" 2>/dev/null | grep -oP '(?<=pid=).*?(?=,|$)')
        elif command -v netstat >/dev/null 2>&1; then
            PID=$(netstat -tulpn 2>/dev/null | grep ":$API_PORT " | awk '{print $7}' | cut -d'/' -f1)
        fi
        
        if [ ! -z "$PID" ]; then
            echo "Killing process $PID using port $API_PORT"
            kill -9 $PID 2>/dev/null || true
        fi
    fi
fi

# Simple port check
portInUse() {
    (echo > /dev/tcp/localhost/$1) >/dev/null 2>&1 && return 0 || return 1
}

# Find an available port for API if 8000 is still in use
if portInUse $API_PORT; then
    echo "Port $API_PORT is still in use, trying alternative ports..."
    for port in {8001..8010}; do
        if ! portInUse $port; then
            echo "Found available port: $port"
            API_PORT=$port
            break
        fi
    done
    
    if portInUse $API_PORT; then
        echo "ERROR: Could not find an available port. Please free port $API_PORT manually."
        exit 1
    fi
fi

# Wait for ports to be completely released
sleep 3

# Setup virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
    source venv/bin/activate
    pip install -r requirements.txt
else
    source venv/bin/activate
fi

# Check if the required commands exist
if ! command -v uvicorn >/dev/null 2>&1; then
    echo "Installing uvicorn..."
    pip install uvicorn
fi

if ! command -v streamlit >/dev/null 2>&1; then
    echo "Installing streamlit..."
    pip install streamlit
fi

# Function to stop all processes on script exit
cleanup() {
    echo "Stopping services..."
    if [ ! -z "$API_PID" ]; then
        kill $API_PID 2>/dev/null || true
    fi
    if [ ! -z "$UI_PID" ]; then
        kill $UI_PID 2>/dev/null || true
    fi
    exit 0
}

# Register the cleanup function for when the script is terminated
trap cleanup SIGINT SIGTERM

# Clear existing log file to start fresh
echo "Clearing log file..."
echo "=== New Session Started $(date) ===" > global.log
chmod 666 global.log 2>/dev/null || true  # Ensure the log file is writable
sync  # Force filesystem sync to ensure changes are written

# Record tracing configuration in log if enabled
if [ "$TRACING_ENABLED" = true ]; then
    echo "=== Tracing Enabled: $OPENAI_TRACE_LEVEL ===" >> global.log
    echo "=== Trace Directory: $OPENAI_TRACE_DIR ===" >> global.log
fi

# Start FastAPI backend
echo "Starting FastAPI backend on http://$API_HOST:$API_PORT..."
uvicorn app_fastapi:app --host $API_HOST --port $API_PORT &
API_PID=$!

# Wait and check if FastAPI started successfully
echo "Waiting for FastAPI to start..."
for i in {1..10}; do
    if curl -s http://$API_HOST:$API_PORT/health >/dev/null 2>&1; then
        echo "FastAPI started successfully!"
        break
    fi
    
    if [ $i -eq 10 ]; then
        echo "ERROR: FastAPI failed to start after 10 attempts. Check logs for errors."
        kill $API_PID 2>/dev/null || true
        exit 1
    fi
    
    echo "Waiting for FastAPI to start (attempt $i/10)..."
    sleep 1
done

# Start Streamlit frontend with the correct API URL
echo "Starting Streamlit frontend on http://$UI_ADDRESS:$UI_PORT..."
export API_URL="http://$API_HOST:$API_PORT"
streamlit run app_streamlit.py --server.port=$UI_PORT --server.address=$UI_ADDRESS &
UI_PID=$!

echo ""
echo "Both services are now running!"
echo "FastAPI: http://$API_HOST:$API_PORT"
echo "Streamlit: http://$UI_ADDRESS:$UI_PORT"
echo "Press Ctrl+C to stop all services."

# Wait for either process to exit
wait $API_PID $UI_PID || true 