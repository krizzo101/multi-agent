#!/bin/bash

# Color codes for terminal output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Default configuration values
DEBUG_MODE=false
TRACE_DIR="./traces"
OPENAI_API_HOST="api.openai.com"
OPENAI_PORT="443"
OPENAI_ORG_ID=""

# Parse command line arguments
for arg in "$@"; do
  case $arg in
    --debug)
      DEBUG_MODE=true
      shift
      ;;
    --trace-dir=*)
      TRACE_DIR="${arg#*=}"
      shift
      ;;
    *)
      # Unknown option
      ;;
  esac
done

echo -e "${BLUE}Starting application with OpenAI Tracing...${NC}"

# Load environment variables from .env file if it exists
if [ -f .env ]; then
    echo -e "${GREEN}Loading environment variables from .env file...${NC}"
    export $(grep -v '^#' .env | xargs)
else
    echo -e "${YELLOW}Warning: .env file not found. Using default configuration.${NC}"
fi

# Check for required environment variables
if [ -z "$OPENAI_API_KEY" ]; then
    echo -e "${RED}Error: OPENAI_API_KEY environment variable is not set. Please add it to your .env file or set it in your environment.${NC}"
    exit 1
fi

# Configure OpenAI settings
echo -e "${BLUE}Configuring OpenAI API settings...${NC}"
export OPENAI_API_HOST="${OPENAI_API_HOST}"
export OPENAI_PORT="${OPENAI_PORT}"
export OPENAI_ORG_ID="${OPENAI_ORG_ID}"
# Explicitly set DEFAULT_LLM to ensure we use OpenAI
export DEFAULT_LLM="openai"

# Configure debug mode
if [ "$DEBUG_MODE" = true ]; then
    echo -e "${YELLOW}Debug mode enabled${NC}"
    export OPENAI_DEBUG=true
    export LOG_LEVEL=DEBUG
    export OTEL_LOG_LEVEL=debug
else
    export LOG_LEVEL=INFO
    export OTEL_LOG_LEVEL=info
fi

# Fix for protobuf compatibility issues
# If you see protobuf errors, run: pip install "protobuf<=3.20.0" --force-reinstall
export PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION=python
echo -e "${BLUE}Setting PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION=python for compatibility${NC}"
echo -e "${YELLOW}Note: If you still see protobuf errors, run: pip install \"protobuf<=3.20.0\" --force-reinstall${NC}"

# Configure OpenTelemetry
echo -e "${BLUE}Setting up OpenTelemetry tracing...${NC}"
export OTEL_SERVICE_NAME="multi-agent-system"
export OTEL_RESOURCE_ATTRIBUTES="deployment.environment=development,service.version=0.1.0"

# Setup tracing directory
if [ ! -d "$TRACE_DIR" ]; then
    echo -e "${YELLOW}Creating trace directory: $TRACE_DIR${NC}"
    mkdir -p "$TRACE_DIR"
fi

# Configure exporters 
export OTEL_TRACES_EXPORTER="console,otlp"
export OTEL_EXPORTER_OTLP_PROTOCOL="http/protobuf"
export OTEL_EXPORTER_OTLP_ENDPOINT="http://localhost:4318"
export OTEL_EXPORTER_OTLP_TRACES_ENDPOINT="http://localhost:4318/v1/traces"

# Display configuration
echo -e "${GREEN}Configuration:${NC}"
echo -e "  - OpenAI API Host: ${OPENAI_API_HOST}"
echo -e "  - Debug Mode: ${DEBUG_MODE}"
echo -e "  - Trace Directory: ${TRACE_DIR}"
echo -e "  - OpenTelemetry Service Name: ${OTEL_SERVICE_NAME}"
echo -e "  - OpenTelemetry Endpoint: ${OTEL_EXPORTER_OTLP_ENDPOINT}"
echo -e "  - LLM Provider: ${DEFAULT_LLM}"

# Launch the application
echo -e "${GREEN}Launching application...${NC}"
./start_app.sh 