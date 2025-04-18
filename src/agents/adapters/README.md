# Adapters Module

## Purpose

The Adapters module provides isolation layers between the core application and external dependencies. This pattern:

1. Reduces coupling between the application and external libraries
2. Makes it easier to handle version conflicts
3. Provides graceful fallbacks when certain features aren't available
4. Simplifies testing by allowing mock implementations

## Current Adapters

### MCPAdapter

The `MCPAdapter` isolates the dependency on the OpenAI Agents SDK's MCP (Model Context Protocol) functionality. It:

- Checks if MCP support is available without causing import errors
- Provides clean interfaces for initializing MCP integration
- Handles tool conversion between LlamaIndex tools and MCP format
- Isolates all imports of the `agents_mcp` package to prevent conflicts

## Usage Example

```python
from src.agents.adapters.mcp_adapter import MCPAdapter

# Check if MCP support is available
if MCPAdapter.has_mcp_support():
    # Initialize MCP with credentials
    MCPAdapter.initialize_mcp_support(api_key="your-api-key")
    
    # Convert a tool to MCP format
    tool = MCPAdapter.convert_to_function_tool(your_tool, schema=your_schema)
else:
    # Fall back to non-MCP approach
    print("MCP support not available, using fallback method")
```

## Adding New Adapters

When adding a new adapter:

1. Create a new file in the `adapters` directory
2. Implement a clean interface that hides external dependencies
3. Use lazy imports to avoid loading dependencies unless needed
4. Add tests to verify both success and fallback paths
5. Update this README with documentation for the new adapter 