#!/bin/bash

# Color codes for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[0;33m'
NC='\033[0m' # No Color

# Script to test the agent template system

echo -e "${BLUE}=========================================================${NC}"
echo -e "${BLUE}    Agent Template System Test                          ${NC}"
echo -e "${BLUE}=========================================================${NC}"

# Ensure python is available
if ! command -v python3 &> /dev/null
then
    echo -e "${YELLOW}Python 3 is not installed. Please install Python 3 to run this test.${NC}"
    exit 1
fi

# Activate virtual environment if it exists
if [ -d "venv" ]; then
    echo -e "${GREEN}Activating virtual environment...${NC}"
    source venv/bin/activate
fi

# Run the test script
echo -e "${GREEN}Running agent template system test...${NC}"
python3 tests/test_agent_templates.py

# Check exit code
if [ $? -eq 0 ]; then
    echo -e "${GREEN}Test completed successfully!${NC}"
else
    echo -e "${YELLOW}Test failed with errors.${NC}"
    exit 1
fi 