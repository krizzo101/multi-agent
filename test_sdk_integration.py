#!/usr/bin/env python3
"""
Integration test for the OpenAI Agents SDK implementation.
This tests our custom OpenAIAgentsSDK class with a simple weather tool.
"""

import os
import sys
import logging
import asyncio
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("sdk-integration-test")

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
    
async def test_sdk_integration():
    """Test our custom OpenAIAgentsSDK implementation"""
    from src.agents.llm.openai_agents_sdk import OpenAIAgentsSDK
    
    # Create our SDK instance
    logger.info("Creating OpenAIAgentsSDK instance")
    sdk = OpenAIAgentsSDK()
    
    # Define a simple weather tool
    def get_weather(location: str) -> str:
        """Get the current weather for a location"""
        return f"The weather in {location} is currently sunny and 72°F."
    
    # Register the tool with the SDK
    logger.info("Registering weather tool")
    sdk.register_tool(get_weather)
    
    # Test a query
    query = "What's the weather like in New York City?"
    logger.info(f"Testing query: {query}")
    
    try:
        # Test the async chat method
        response = await sdk.achat(query)
        logger.info(f"SDK response: {response}")
        
        # Skip streaming for now as it needs more work
        logger.info("Skipping streaming test for now")
        
        return True
    except Exception as e:
        logger.error(f"Error in SDK test: {str(e)}")
        return False

async def main():
    """Main function to run tests"""
    # Setup environment
    setup_environment()
    
    # Run the test
    success = await test_sdk_integration()
    
    # Exit with appropriate code
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    asyncio.run(main()) 