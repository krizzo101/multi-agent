"""
Adapter for the Model Context Protocol (MCP) functionality.

This module isolates the dependencies on MCP-related packages and provides
a clean interface for the main codebase.
"""

import logging
import os
from typing import Any, Callable, Dict, List, Optional

from llama_index.core.tools import FunctionTool

logger = logging.getLogger(__name__)

# Disable telemetry for the OpenAI Agents SDK
os.environ["OPENAI_AGENTS_TELEMETRY_ENABLED"] = "false"

class MCPAdapter:
    """
    Adapter for integrating with MCP functionality.
    
    This class isolates the dependencies on MCP-related packages and provides
    methods for converting tools to and from MCP format.
    """
    
    @staticmethod
    def initialize_mcp_support(api_key: str = None, org_id: str = "") -> bool:
        """
        Initialize MCP support with the given API key and organization ID.
        
        Args:
            api_key: Optional OpenAI API key
            org_id: Optional OpenAI organization ID
            
        Returns:
            True if initialization was successful, False otherwise
        """
        try:
            # Set environment variables for the Agents SDK to use
            if api_key:
                os.environ["OPENAI_API_KEY"] = api_key
            if org_id:
                os.environ["OPENAI_ORG_ID"] = org_id
            
            # Disable telemetry
            os.environ["OPENAI_AGENTS_TELEMETRY_ENABLED"] = "false"
            
            # Try direct import first
            try:
                from agents_mcp import MCPUtil
                return True
            except (ImportError, AttributeError):
                # Try the fallback approach by importing the main package
                from openai_agents_mcp import register_mcp_tools
                return True
            
        except ImportError:
            logger.warning("MCP support is not available. Please install openai-agents-mcp.")
            return False
        except Exception as e:
            logger.error(f"Failed to initialize MCP support: {str(e)}")
            return False
    
    @staticmethod
    def convert_to_function_tool(function_tool: FunctionTool, schema: Dict[str, Any] = None) -> Any:
        """
        Convert a FunctionTool to a format compatible with the Agents SDK.
        
        Args:
            function_tool: The FunctionTool to convert
            schema: Optional schema to use for the tool
            
        Returns:
            A function tool compatible with the Agents SDK
        """
        try:
            # Import the function_tool decorator
            from agents import function_tool as sdk_function_tool
            
            # Clean the schema to remove unsupported properties
            if schema:
                schema = MCPAdapter._clean_schema_for_openai(schema)
            
            # Create a function_tool wrapper around the original function
            @sdk_function_tool
            def wrapped_tool(**kwargs):
                return function_tool.fn(**kwargs)
            
            # Set the metadata and schema to match the original tool
            wrapped_tool.name = function_tool.metadata.name
            wrapped_tool.description = function_tool.metadata.description
            
            # If a schema is provided, use it
            if schema:
                wrapped_tool.params_schema = schema
            
            return wrapped_tool
        except ImportError as e:
            logger.error(f"Failed to import MCP dependencies: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Error converting tool {function_tool.metadata.name}: {str(e)}")
            raise
    
    @staticmethod
    def _clean_schema_for_openai(schema: Dict[str, Any]) -> Dict[str, Any]:
        """
        Clean a JSON schema for OpenAI compatibility by removing unsupported fields.
        
        OpenAI doesn't support 'default' in function parameters.
        
        Args:
            schema: The schema to clean
            
        Returns:
            The cleaned schema
        """
        # Make a deep copy to avoid modifying the original
        import copy
        cleaned_schema = copy.deepcopy(schema)
        
        # Remove unsupported fields recursively
        if 'properties' in cleaned_schema:
            for prop_name, prop_value in cleaned_schema['properties'].items():
                if isinstance(prop_value, dict):
                    # Remove 'default' field if present
                    if 'default' in prop_value:
                        del prop_value['default']
                        
                    # Process nested properties
                    if 'properties' in prop_value:
                        prop_value = MCPAdapter._clean_schema_for_openai(prop_value)
        
        return cleaned_schema
    
    @staticmethod
    def import_mcp_util():
        """
        Import MCP functionality from appropriate package.
        
        Returns:
            The MCP utility class or function
        
        Raises:
            ImportError: If the openai-agents-mcp package is not installed
        """
        try:
            # Try direct import first
            try:
                from agents_mcp import MCPUtil
                return MCPUtil
            except (ImportError, AttributeError):
                # Try the fallback approach
                from openai_agents_mcp import register_mcp_tools
                return register_mcp_tools
        except ImportError as e:
            logger.error(f"Failed to import MCP functionality: {str(e)}")
            logger.error("Please install the openai-agents-mcp package: pip install openai-agents-mcp")
            raise
    
    @staticmethod
    def has_mcp_support() -> bool:
        """
        Check if MCP support is available.
        
        Returns:
            True if MCP support is available, False otherwise
        """
        try:
            MCPAdapter.import_mcp_util()
            return True
        except (ImportError, AttributeError):
            return False 