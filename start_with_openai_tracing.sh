#!/bin/bash

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Parse command line arguments
DEBUG=false
TRACE_LEVEL="basic"  # Default trace level

function print_usage() {
  echo -e "${BLUE}Usage:${NC} $0 [options]"
  echo -e "Options:"
  echo -e "  --debug              Enable debug mode with verbose logging"
  echo -e "  --trace-level=LEVEL  Set tracing level (basic, detailed, or full)"
  echo -e "  --help               Show this help message"
}

# Parse command line arguments
for arg in "$@"; do
  case $arg in
    --debug)
      DEBUG=true
      shift
      ;;
    --trace-level=*)
      TRACE_LEVEL="${arg#*=}"
      shift
      ;;
    --help)
      print_usage
      exit 0
      ;;
  esac
done

echo -e "${BLUE}╔══════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║${NC}             ${GREEN}OpenAI Agents SDK with Tracing${NC}              ${BLUE}║${NC}"
echo -e "${BLUE}╚══════════════════════════════════════════════════════════╝${NC}"

# Load environment variables
if [ -f .env ]; then
  echo -e "${GREEN}Loading environment variables from .env file${NC}"
  source .env
else
  echo -e "${YELLOW}No .env file found, using defaults${NC}"
fi

# Ensure OPENAI_API_KEY is set
if [ -z "$OPENAI_API_KEY" ]; then
  echo -e "${RED}ERROR: OPENAI_API_KEY is not set. Please set it in your .env file or environment.${NC}"
  exit 1
fi

# Configure OpenAI settings
export DEFAULT_LLM="openai"
export OPENAI_API_HOST=${OPENAI_API_HOST:-"api.openai.com"}
export OPENAI_ORG_ID=${OPENAI_ORG_ID:-""}
export API_HOST=${API_HOST:-"0.0.0.0"}
export API_PORT=${API_PORT:-"8000"}
export UI_PORT=${UI_PORT:-"8501"}
export UI_ADDRESS=${UI_ADDRESS:-"0.0.0.0"}

# Enable debug mode if requested
if [ "$DEBUG" = true ]; then
  echo -e "${YELLOW}Debug mode enabled${NC}"
  export OPENAI_DEBUG="true"
  export LOG_LEVEL="DEBUG"
else
  export OPENAI_DEBUG="false"
  export LOG_LEVEL="INFO"
fi

# Setup tracing directory
TRACES_DIR="traces"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
TRACE_SESSION_DIR="${TRACES_DIR}/${TIMESTAMP}"

# Create trace directories
if [ ! -d "$TRACES_DIR" ]; then
  echo -e "${GREEN}Creating traces directory${NC}"
  mkdir -p "$TRACES_DIR"
fi

if [ ! -d "$TRACE_SESSION_DIR" ]; then
  mkdir -p "$TRACE_SESSION_DIR"
fi

# Set up tracing configuration based on trace level
case "$TRACE_LEVEL" in
  "basic")
    echo -e "${GREEN}Setting up basic tracing${NC}"
    export OPENAI_TRACE_LEVEL="basic"
    ;;
  "detailed")
    echo -e "${GREEN}Setting up detailed tracing${NC}"
    export OPENAI_TRACE_LEVEL="detailed"
    export OPENAI_BETA="traces=v1"
    ;;
  "full")
    echo -e "${GREEN}Setting up full tracing with visualization${NC}"
    export OPENAI_TRACE_LEVEL="full"
    export OPENAI_BETA="traces=v1,enhanced_traces=v1"
    # Enable additional headers for trace visualization
    export OPENAI_TRACE_VIZ="true"
    ;;
  *)
    echo -e "${YELLOW}Unknown trace level: $TRACE_LEVEL. Using basic.${NC}"
    export OPENAI_TRACE_LEVEL="basic"
    ;;
esac

# Configure trace export location
export OPENAI_TRACE_DIR="$TRACE_SESSION_DIR"
export OPENAI_AGENTS_TRACE_EXPORT="true"

# Log configuration details
echo -e "${GREEN}Configuration:${NC}"
echo -e "  ${BLUE}API Host:${NC} $API_HOST:$API_PORT"
echo -e "  ${BLUE}UI Host:${NC} $UI_ADDRESS:$UI_PORT"
echo -e "  ${BLUE}LLM Provider:${NC} OpenAI Agents SDK"
echo -e "  ${BLUE}Debug Mode:${NC} $DEBUG"
echo -e "  ${BLUE}Organization ID:${NC} ${OPENAI_ORG_ID:-Not set}"
echo -e "  ${BLUE}Trace Level:${NC} $TRACE_LEVEL"
echo -e "  ${BLUE}Trace Directory:${NC} $TRACE_SESSION_DIR"

echo -e "${YELLOW}Tracing will be saved to: ${TRACE_SESSION_DIR}${NC}"
echo -e "${GREEN}Starting application with OpenAI Agents SDK and tracing enabled${NC}"

# Launch the application using the main start script
./start_app.sh

# After the application exits, summarize trace information
TRACE_COUNT=$(find "$TRACE_SESSION_DIR" -type f | wc -l)
echo -e "\n${GREEN}Session completed.${NC}"
echo -e "${BLUE}Traces saved:${NC} $TRACE_COUNT files in $TRACE_SESSION_DIR"
echo -e "${YELLOW}To visualize traces, run: python -m agents.viz.trace_viewer $TRACE_SESSION_DIR${NC}" 