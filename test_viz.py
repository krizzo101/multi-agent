#!/usr/bin/env python3
"""
Test script for the OpenAI Agents SDK visualization features.
This script creates a simple agent system with specialized agents and tools,
then generates a visualization of the agent system.
"""

import os
import sys
import logging
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("openai-agents-viz")

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

def create_agent_system():
    """Create a system of agents and visualize it"""
    # Import required modules
    from agents import Agent, function_tool
    from agents.viz import visualize_agent_system
    
    # Create tools
    @function_tool
    def get_weather(location: str) -> str:
        """Get the current weather for a location"""
        return f"The weather in {location} is currently sunny and 72°F."
    
    @function_tool
    def search_flights(from_location: str, to_location: str, date: str) -> list:
        """Search for flights between two locations on a given date"""
        return [
            {"airline": "Acme Air", "departure": "8:00 AM", "price": "$300"},
            {"airline": "Sky Airlines", "departure": "10:30 AM", "price": "$350"},
            {"airline": "Global Airways", "departure": "2:15 PM", "price": "$275"}
        ]
    
    # Create the specialized agents
    travel_agent = Agent(
        name="Travel Assistant",
        instructions="You help users find and book travel arrangements.",
        tools=[search_flights],
        model="o3-mini"  # Use a widely available model
    )
    
    weather_agent = Agent(
        name="Weather Assistant",
        instructions="You provide weather information to users.",
        tools=[get_weather],
        model="o3-mini"  # Use a widely available model
    )
    
    # Create a main agent that can use the specialized agents as tools
    trip_planner = Agent(
        name="Trip Planner",
        instructions="You help users plan trips by coordinating with specialized assistants.",
        tools=[
            travel_agent.as_tool(
                tool_name="find_travel_options",
                tool_description="Find travel options for the user's trip"
            ),
            weather_agent.as_tool(
                tool_name="get_destination_weather",
                tool_description="Get weather information for the destination"
            )
        ],
        model="o3-mini"  # Use a widely available model
    )
    
    # Visualize the agent system
    logger.info("Generating agent system visualization...")
    graph = visualize_agent_system([trip_planner, travel_agent, weather_agent])
    
    # Save the graph to a file
    output_file = "agent_system.png"
    graph.render(filename="agent_system", format="png", cleanup=True)
    logger.info(f"Visualization saved to {output_file}")
    
    return True

def main():
    """Main function to run tests"""
    # Set up environment
    setup_environment()
    
    # Create and visualize the agent system
    success = create_agent_system()
    
    # Exit with appropriate code
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main() 