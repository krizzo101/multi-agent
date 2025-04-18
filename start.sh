#!/bin/bash
# Startup script for the multi-agent application
# Usage: ./start.sh [--debug]

# Set default configuration
export DEFAULT_LLM="gpt-4-turbo-preview"
CONFIG_FILE=".env"

# Parse command line arguments
DEBUG_MODE=false

while [[ "$#" -gt 0 ]]; do
    case $1 in
        --debug) DEBUG_MODE=true ;;
        *) echo "Unknown parameter: $1"; exit 1 ;;
    esac
    shift
done

# Load environment variables if config file exists
if [[ -f "$CONFIG_FILE" ]]; then
    echo "Loading configuration from $CONFIG_FILE"
    source "$CONFIG_FILE"
else
    echo "No $CONFIG_FILE file found, using default configuration"
fi

# Check for required environment variables
if [[ -z "$OPENAI_API_KEY" ]]; then
    echo "Error: OPENAI_API_KEY is not set"
    echo "Please set the OPENAI_API_KEY environment variable or add it to your $CONFIG_FILE file"
    exit 1
fi

# Set debug mode if requested
if [[ "$DEBUG_MODE" == true ]]; then
    echo "Starting application in DEBUG mode"
    export OPENAI_DEBUG=true
    # Additional debug settings
    export PYTHONVERBOSE=1
    LOG_LEVEL="DEBUG"
else
    echo "Starting application in NORMAL mode"
    export OPENAI_DEBUG=false
    LOG_LEVEL="INFO"
fi

# Print configuration
echo "Configuration:"
echo "- LLM Model: $DEFAULT_LLM"
echo "- Debug Mode: $OPENAI_DEBUG"
echo "- Log Level: $LOG_LEVEL"
echo "- Organization: ${OPENAI_ORG_ID}"
echo "- Project: ${OPENAI_PROJECT_ID}"

# Start the application
echo "Starting multi-agent application..."
python3 -m src.app --log-level="$LOG_LEVEL" 