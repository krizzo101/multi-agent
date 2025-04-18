# MCP Tools Integration with OpenAI Agents SDK

This document explains how to use Machine Conversation Protocol (MCP) tools with the OpenAI Agents SDK integration.

## Overview

Machine Conversation Protocol (MCP) is a standard for connecting large language models (LLMs) to external tools and services. Our implementation allows agents to access powerful external tools, such as:

- **Brave Search**: Web search capabilities using the Brave Search API
- **Future MCP tools**: Additional services like databases, document storage, specialized APIs, etc.

## Brave Search MCP Tool

The `BraveSearchTool` provides a simple interface for agents to search the web using the Brave Search API.

### Configuration

To use the Brave Search tool, you need to set up API credentials:

1. Get a Brave Search API key from https://brave.com/search/api/
2. Add your API key to your environment variables or .env file:

```
BRAVE_SEARCH_API_KEY=your_api_key_here
BRAVE_SEARCH_SUBSCRIPTION_KEY=your_subscription_key_here  # If required
```

### Usage in Code

The tool is automatically registered with the OpenAI Agents SDK when using the default agent configuration:

```python
from src.agents.llm import OpenAIAgentsSDK
from src.tools.brave_search import brave_search_tool

# Create SDK instance
sdk = OpenAIAgentsSDK()

# Register the MCP tool
sdk.register_mcp_tool(brave_search_tool)

# Process a query that might need search
response = sdk.chat("What are the latest developments in quantum computing?")
```

### Search Parameters

The Brave Search tool supports these parameters:

- `query` (string): The search query
- `count` (int, default=5): Number of results to return (1-20)
- `country` (string, default="US"): Two-letter country code
- `freshness` (string, optional): Filter for freshness ("day", "week", "month")
- `safe_search` (string, default="moderate"): Safe search level ("off", "moderate", "strict")

## Adding New MCP Tools

You can create your own MCP tools by following this pattern:

1. Create a tool class that implements the needed functionality
2. Create a FunctionTool instance using `as_function_tool()`
3. Register the tool with the OpenAI Agents SDK using `register_mcp_tool()`

Example:

```python
from typing import Dict, Any
from llama_index.core.tools import FunctionTool

class CustomMCPTool:
    def execute_action(self, param1: str, param2: int) -> Dict[str, Any]:
        """Execute a custom action with parameters"""
        # Implementation here
        return {"result": f"Processed {param1} with value {param2}"}
        
    def as_function_tool(self) -> FunctionTool:
        return FunctionTool.from_defaults(
            name="custom_mcp_tool",
            fn=self.execute_action,
            description="Execute a custom action with parameters"
        )

# Create and register the tool
custom_tool = CustomMCPTool().as_function_tool()
sdk.register_mcp_tool(custom_tool)
```

## Agent Interactions with MCP Tools

The Smart Agent Proxy system will automatically route requests to the appropriate agent with the right tools:

1. The `ReflectionAgent` is equipped with the Brave Search tool for information retrieval
2. The `PlanningAgent` has access to all available tools
3. When using the OpenAI Agents SDK directly, all registered tools are available

The routing system intelligently directs queries that might need web search (containing keywords like "search", "find", "what is", etc.) to the appropriate agent with search capabilities.

## Tracing and Debugging

To view detailed information about MCP tool calls:

1. Use the tracing functionality in the OpenAI Agents SDK
2. Enable debug logging by setting `OPENAI_DEBUG=true`
3. Check the logs for tool registration and execution details

Example with debug mode:

```bash
# Run with debug mode enabled to see detailed tool execution
OPENAI_DEBUG=true ./start_with_openai_tracing.sh
```

## Limitations and Considerations

- MCP tools depend on external services and APIs which may have rate limits or usage costs
- Brave Search API has specific usage limits and requirements - check Brave Search documentation
- For production use, implement proper error handling and fallbacks for MCP tool failures 