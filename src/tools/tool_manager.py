from typing import Callable, Optional, List, Dict, Any
from llama_index.core.tools import FunctionTool

# Import the BraveSearchTool
from .brave_search import brave_search_tool, BraveSearchTool

def create_function_tool(
    func: Callable,
    name: Optional[str] = None,
    description: Optional[str] = None
) -> FunctionTool:
    """Helper function to create a FunctionTool with proper metadata"""
    return FunctionTool.from_defaults(
        fn=func,
        name=name or func.__name__,
        description=description or func.__doc__ or "No description provided"
    )

def get_weather(location: str, unit: str) -> dict:
    """Get current weather for a location"""
    # Default to celsius if no unit is provided
    unit = unit.lower() if unit else "celsius"
    
    # Mock weather data
    return {
        "temperature": 25,
        "unit": unit,
        "weather_description": "Sunny",
        "humidity": 60,
        "wind_speed": 10
    }

# Create the weather tool with explicit schema
weather_tool = FunctionTool.from_defaults(
    fn=get_weather,
    name="get_weather",
    description="Get current weather information for a location",
    fn_schema={
        "type": "object",
        "properties": {
            "location": {
                "type": "string",
                "description": "The city or location to get weather for"
            },
            "unit": {
                "type": "string",
                "description": "The temperature unit (celsius or fahrenheit)",
                "enum": ["celsius", "fahrenheit"]
            }
        },
        "required": ["location"]
    }
)

# Function to get all available tools
def get_all_tools() -> List[FunctionTool]:
    """Get all available tools that can be used by agents"""
    return [
        weather_tool,
        brave_search_tool
    ]

# Function to convert function tools to MCP tool format for OpenAI
def convert_to_mcp_tool(tool: FunctionTool) -> Dict[str, Any]:
    """Convert a FunctionTool to MCP tool format for OpenAI"""
    tool_schema = tool.metadata.get_parameters_dict()
    
    # Clean schema for OpenAI compatibility
    if "properties" in tool_schema:
        for prop_name, prop_value in tool_schema["properties"].items():
            if isinstance(prop_value, dict):
                # Remove 'default' field if present - OpenAI doesn't support it
                if "default" in prop_value:
                    del prop_value["default"]
    
    return {
        "type": "function",
        "function": {
            "name": tool.metadata.name,
            "description": tool.metadata.description,
            "parameters": tool_schema
        }
    }