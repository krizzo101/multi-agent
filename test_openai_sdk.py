#!/usr/bin/env python3
"""
Test script for verifying the OpenAI Agents SDK integration.
This script tests both normal operation and error handling.
"""

import os
import sys
import json
import argparse
import logging
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("openai-sdk-test")

# Ensure the src directory is in the path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description='Test OpenAI Agents SDK Integration')
    parser.add_argument('--debug', action='store_true', help='Enable debug logging')
    parser.add_argument('--test-error', action='store_true', help='Test error handling')
    return parser.parse_args()

def load_environment():
    """Load environment variables from .env file if it exists."""
    if os.path.exists('.env'):
        logger.info("Loading environment variables from .env file")
        load_dotenv()
    else:
        logger.warning("No .env file found. Ensure OPENAI_API_KEY is set in your environment.")

def verify_api_key():
    """Verify that the OpenAI API key is set."""
    api_key = os.environ.get('OPENAI_API_KEY')
    if not api_key:
        logger.error("OPENAI_API_KEY environment variable is not set")
        sys.exit(1)
    return api_key

def test_agents_sdk_normal():
    """Test the OpenAI Agents SDK integration with normal operation."""
    logger.info("Testing OpenAI Agents SDK with normal operation")
    
    try:
        # Import here to avoid circular imports
        from src.agents.llm.openai_agents_sdk import OpenAIAgentsSDK
        from agents import tool
        
        # Define a simple test tool
        @tool
        def weather(location: str) -> str:
            """Get the weather for a location"""
            return f"Weather for {location}: Sunny, 75°F"
        
        # Create SDK instance
        sdk = OpenAIAgentsSDK()
        
        # Register the tool
        sdk.register_tool(weather)
        
        # Test with a query that should use the tool
        query = "What's the weather in New York?"
        logger.info(f"Sending query to SDK: {query}")
        
        # Use the chat method
        response = sdk.chat(query)
        logger.info(f"Response: {response}")
        
        logger.info("OpenAI Agents SDK test completed successfully")
        return True
    except Exception as e:
        logger.error(f"Error testing OpenAI Agents SDK: {str(e)}")
        return False

def test_agents_sdk_error():
    """Test error handling in the OpenAI Agents SDK."""
    logger.info("Testing OpenAI Agents SDK error handling")
    
    # Save original API key
    original_key = os.environ.get("OPENAI_API_KEY")
    
    try:
        # Set invalid API key
        os.environ["OPENAI_API_KEY"] = "invalid-key-for-testing"
        
        # Import here to avoid circular imports
        from src.agents.llm.openai_agents_sdk import OpenAIAgentsSDK
        
        # Create SDK instance with invalid key
        sdk = OpenAIAgentsSDK()
        
        # Try to use it
        query = "This should fail"
        logger.info(f"Sending query with invalid API key: {query}")
        
        response = sdk.chat(query)
        logger.error(f"Error: Expected exception but got response: {response}")
        return False
    except Exception as e:
        logger.info(f"Successfully caught expected error: {str(e)}")
        return True
    finally:
        # Restore original API key
        if original_key:
            os.environ["OPENAI_API_KEY"] = original_key

def main():
    """Main function to run the tests."""
    args = parse_arguments()
    
    # Set debug mode if requested
    if args.debug:
        logger.setLevel(logging.DEBUG)
        os.environ["OPENAI_DEBUG"] = "true"
        logger.debug("Debug mode enabled")
    else:
        os.environ["OPENAI_DEBUG"] = "false"
    
    # Load environment variables
    load_environment()
    
    # Verify API key
    verify_api_key()
    
    # Setup environment for tests
    os.environ["DEFAULT_LLM"] = "openai"
    
    # Track results
    test_results = {
        "agents_sdk_normal": None,
        "agents_sdk_error": None
    }
    
    # Run normal operation test
    test_results["agents_sdk_normal"] = test_agents_sdk_normal()
    
    # Run error test if requested
    if args.test_error:
        test_results["agents_sdk_error"] = test_agents_sdk_error()
    
    # Print summary
    logger.info("\n----- Test Results -----")
    for test_name, result in test_results.items():
        if result is None:
            status = "SKIPPED"
        elif result:
            status = "PASSED"
        else:
            status = "FAILED"
        logger.info(f"{test_name}: {status}")
    
    # Check for failures
    failed_tests = [k for k, v in test_results.items() if v is False]
    if failed_tests:
        logger.error(f"Failed tests: {', '.join(failed_tests)}")
        sys.exit(1)
    else:
        logger.info("All executed tests passed!")
        sys.exit(0)

if __name__ == "__main__":
    main() 