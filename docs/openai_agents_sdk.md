# OpenAI Agents SDK Integration

This document explains how to use the OpenAI Agents SDK integration in the Multi-Agent Framework.

## Overview

The OpenAI Agents SDK is a powerful toolkit for building agent systems with features like:

- Built-in agent loops with tool handling
- Tracing and visualization 
- Handoffs between agents
- Performance monitoring

Our integration provides a seamless way to use these capabilities within the Multi-Agent Framework.

## Configuration

The SDK can be configured through environment variables or the `config.yaml` file:

```yaml
agents_sdk:
  enabled: true
  api_key: ""  # Will use OPENAI_API_KEY environment variable if not set
  model_id: ${OPENAI_MODEL_ID}
  debug: false
  organization_id: ""  # Will use OPENAI_ORG_ID environment variable if not set
  project_id: ""  # Will use OPENAI_PROJECT_ID environment variable if not set
```

## Environment Variables

The SDK supports the following environment variables:

- `OPENAI_API_KEY`: Your OpenAI API key (required)
- `OPENAI_ORG_ID`: Your OpenAI organization ID (optional)
- `OPENAI_PROJECT_ID`: Your project identifier (optional)
- `OPENAI_API_HOST`: OpenAI API host address (optional)
- `OPENAI_API_BASE`: OpenAI API base URL (optional)

## Basic Usage

Here's a simple example of using the SDK:

```python
from src.agents.llm import OpenAIAgentsSDK

# Create SDK instance
sdk = OpenAIAgentsSDK()

# Define a weather tool
def get_weather(location: str) -> str:
    """Get the current weather for a location"""
    return f"The weather in {location} is currently sunny and 72°F."

# Register the tool with the SDK
sdk.register_tool(get_weather)

# Use the SDK to chat
async def chat_with_sdk():
    response = await sdk.achat("What's the weather in New York?")
    print(response)
```

## Agent Router Integration

The SDK integrates with the Multi-Agent Framework's Smart Agent Proxy:

```python
from src.agents import SmartAgentProxy, AgentOptions
from src.agents.llm import OpenAIAgentsSDK

# Create the SDK instance
llm = OpenAIAgentsSDK()

# Create the Smart Agent Proxy with the SDK
proxy = SmartAgentProxy(
    llm,
    AgentOptions(
        id="proxy",
        name="Smart Agent Proxy",
        description="Intelligently routes requests to specialized agents"
    )
)

# Register agents and use the proxy
# ...
```

## Advanced Features

### Tool Registration

You can register custom tools with the SDK:

```python
from agents import function_tool

@function_tool
def search_database(query: str) -> list:
    """Search the database for information"""
    # Implementation...
    return results

sdk.register_tool(search_database)
```

### Asynchronous Usage

The SDK supports both synchronous and asynchronous usage:

```python
# Synchronous
response = sdk.chat("How can I help you?")

# Asynchronous 
response = await sdk.achat("How can I help you?")
```

## Troubleshooting

If you encounter issues:

1. Make sure your OpenAI API key is valid and has access to the model you're using
2. Use `gpt-4o-mini` model for best compatibility
3. Enable debug mode by setting `OPENAI_DEBUG=true`

## Visualization (Future Enhancement)

The SDK also supports visualizing agent systems. This feature requires installing the visualization package:

```bash
pip install "openai-agents[viz]"
```

Example code for visualization:

```python
from agents import Agent, function_tool
from agents.viz import visualize_agent_system

# Create agents and tools
# ...

# Visualize the agent system
graph = visualize_agent_system([agent1, agent2, agent3])
graph.render(filename="agent_system", format="png", cleanup=True)
``` 