#!/bin/bash

# Enhanced start script with OpenTelemetry tracing support
# This script configures and launches the application with tracing enabled

# Color codes for pretty output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
MAGENTA='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Print banner
echo -e "${BLUE}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║                                                            ║${NC}"
echo -e "${BLUE}║${GREEN}             MULTI-AGENT SYSTEM - TRACING ENABLED            ${BLUE}║${NC}"
echo -e "${BLUE}║                                                            ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════════╝${NC}"

# Parse command line arguments
DEBUG_MODE=false
EXPORTER_TYPE="console"
SAMPLING_RATIO=1.0
ENDPOINT=""

# Process arguments
while [[ $# -gt 0 ]]; do
  case $1 in
    --debug)
      DEBUG_MODE=true
      shift
      ;;
    --exporter)
      EXPORTER_TYPE="$2"
      shift 2
      ;;
    --endpoint)
      ENDPOINT="$2"
      shift 2
      ;;
    --sampling)
      SAMPLING_RATIO="$2"
      shift 2
      ;;
    --help)
      echo -e "Usage: $0 [options]"
      echo -e "Options:"
      echo -e "  --debug               Enable debug mode for verbose logging"
      echo -e "  --exporter TYPE       Specify the tracing exporter type (console, otlp, jaeger)"
      echo -e "  --endpoint URL        Specify the exporter endpoint URL"
      echo -e "  --sampling RATIO      Specify the sampling ratio (0.0-1.0)"
      echo -e "  --help                Display this help message"
      exit 0
      ;;
    *)
      echo -e "${RED}Unknown option: $1${NC}"
      echo -e "Use --help for usage information"
      exit 1
      ;;
  esac
done

# Load environment variables from .env file if it exists
if [ -f .env ]; then
    echo -e "${GREEN}Loading environment variables from .env file...${NC}"
    export $(grep -v '^#' .env | xargs)
else
    echo -e "${YELLOW}Warning: .env file not found. Using default environment variables.${NC}"
fi

# Check if OPENAI_API_KEY is set
if [ -z "$OPENAI_API_KEY" ]; then
    echo -e "${RED}Error: OPENAI_API_KEY environment variable is not set.${NC}"
    echo -e "${YELLOW}Please set it in your .env file or export it directly.${NC}"
    exit 1
fi

# Set up OpenAI API configuration
export OPENAI_API_HOST=${OPENAI_API_HOST:-"https://api.openai.com"}
export OPENAI_API_PORT=${OPENAI_API_PORT:-"443"}
export OPENAI_ORG_ID=${OPENAI_ORG_ID:-""}
export OPENAI_PROJECT_ID=${OPENAI_PROJECT_ID:-""}

# Configure log level
if [ "$DEBUG_MODE" = true ]; then
    export LOG_LEVEL="DEBUG"
    echo -e "${YELLOW}Debug mode enabled. Setting log level to DEBUG.${NC}"
else
    export LOG_LEVEL="INFO"
fi

# Set up tracing directory
TRACE_DIR="./traces"
mkdir -p $TRACE_DIR

# Configure tracer based on exporter type
export OTEL_SERVICE_NAME="multi-agent-system"
export OTEL_TRACES_SAMPLER="parentbased_traceidratio"
export OTEL_TRACES_SAMPLER_ARG="$SAMPLING_RATIO"
export OTEL_RESOURCE_ATTRIBUTES="service.name=multi-agent-system,deployment.environment=development,service.version=0.1.0"

case $EXPORTER_TYPE in
    "console")
        export TRACER_EXPORTER="console"
        echo -e "${GREEN}Using console exporter for traces${NC}"
        ;;
    "otlp")
        export TRACER_EXPORTER="otlp"
        if [ -n "$ENDPOINT" ]; then
            export OTEL_EXPORTER_OTLP_ENDPOINT="$ENDPOINT"
        else
            export OTEL_EXPORTER_OTLP_ENDPOINT="http://localhost:4317"
        fi
        echo -e "${GREEN}Using OTLP exporter for traces with endpoint: ${OTEL_EXPORTER_OTLP_ENDPOINT}${NC}"
        ;;
    "jaeger")
        export TRACER_EXPORTER="jaeger"
        if [ -n "$ENDPOINT" ]; then
            export OTEL_EXPORTER_JAEGER_ENDPOINT="$ENDPOINT"
        else
            export OTEL_EXPORTER_JAEGER_ENDPOINT="localhost:6831"
        fi
        echo -e "${GREEN}Using Jaeger exporter for traces with endpoint: ${OTEL_EXPORTER_JAEGER_ENDPOINT}${NC}"
        ;;
    *)
        echo -e "${YELLOW}Unknown exporter type: $EXPORTER_TYPE. Defaulting to console exporter.${NC}"
        export TRACER_EXPORTER="console"
        ;;
esac

# Display configuration
echo -e "\n${CYAN}Configuration:${NC}"
echo -e "  ${BLUE}OpenAI API Host:${NC} $OPENAI_API_HOST"
echo -e "  ${BLUE}Debug Mode:${NC} $DEBUG_MODE"
echo -e "  ${BLUE}Log Level:${NC} $LOG_LEVEL"
echo -e "  ${BLUE}Exporter Type:${NC} $TRACER_EXPORTER"
echo -e "  ${BLUE}Sampling Ratio:${NC} $SAMPLING_RATIO"

if [ "$TRACER_EXPORTER" = "otlp" ]; then
    echo -e "  ${BLUE}OTLP Endpoint:${NC} $OTEL_EXPORTER_OTLP_ENDPOINT"
elif [ "$TRACER_EXPORTER" = "jaeger" ]; then
    echo -e "  ${BLUE}Jaeger Endpoint:${NC} $OTEL_EXPORTER_JAEGER_ENDPOINT"
fi

echo -e "\n${GREEN}Starting application with tracing enabled...${NC}\n"

# Start the application with regular start script
./start_app.sh 