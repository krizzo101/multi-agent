#!/usr/bin/env python3
"""
Simple test script for the OpenAI Agents SDK.
This script creates a basic agent with a weather tool to verify functionality.
"""

import os
import sys
import logging
import asyncio
import json
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("openai-agents-basic")

# Make sure src is in the path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

def setup_environment():
    """Load environment variables and check for API key"""
    # Load from .env file if it exists
    if os.path.exists('.env'):
        logger.info("Loading environment variables from .env file")
        load_dotenv()
    
    # Check for required API key
    api_key = os.environ.get('OPENAI_API_KEY')
    if not api_key:
        logger.error("OPENAI_API_KEY environment variable is not set")
        sys.exit(1)
    
    # Print all OpenAI-related environment variables for debugging
    openai_vars = {k: v for k, v in os.environ.items() if 'OPENAI' in k.upper()}
    logger.info(f"OpenAI environment variables: {json.dumps(openai_vars)}")

async def test_basic_agent():
    """Test a basic agent with a weather tool"""
    from agents import Agent, function_tool, Runner
    
    # Create a simple weather tool
    @function_tool
    def get_weather(location: str) -> str:
        """Get the current weather for a location"""
        return f"The weather in {location} is currently sunny and 72°F."
    
    # Create an agent with the tool
    logger.info("Creating agent with the weather tool")
    agent = Agent(
        name="Weather Assistant",
        instructions="You help users with weather information.",
        tools=[get_weather],
        model="o3-mini"  # Using base model without date suffix
    )
    
    # Test a query
    query = "What's the weather like in San Francisco?"
    logger.info(f"Testing query: {query}")
    
    try:
        # Enable debug mode for more information
        os.environ["OPENAI_DEBUG"] = "true"
        
        # Run the agent
        result = await Runner.run(agent, query)
        logger.info(f"Agent response: {result.final_output}")
        return True
    except Exception as e:
        logger.error(f"Error running agent: {str(e)}")
        
        # If there's a response error with details, print them
        if hasattr(e, 'response') and hasattr(e.response, 'text'):
            logger.error(f"Response error details: {e.response.text}")
        
        return False

async def main():
    """Main function to run tests"""
    # Setup environment
    setup_environment()
    
    # Run the test
    success = await test_basic_agent()
    
    # Exit with appropriate code
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    asyncio.run(main()) 