"""
OpenAI Agents SDK implementation for the Multi-Agent Framework.

This module provides an implementation of the LLM interface using OpenAI's API,
with fallbacks for the Agents SDK functionality.
"""

import os
import logging
import asyncio
import json
from typing import List, Optional, AsyncGenerator, Generator, Dict, Any, Callable
from contextlib import asynccontextmanager
import uuid

# Set up logger first to avoid reference before definition
logger = logging.getLogger(__name__)

# Standard OpenAI imports
import openai
from openai import OpenAI
from openai import AsyncOpenAI
from openai import BadRequestError

# Local imports
from llama_index.core.llms import ChatMessage
from llama_index.core.tools import FunctionTool
from .base import BaseLLM
from src.settings import global_settings
from src.agents.utils.pattern import safe_extract_content
from src.tools.tool_manager import convert_to_mcp_tool
from src.agents.adapters.mcp_adapter import MCPAdapter

# Custom exception for agent creation failures
class AgentCreationError(Exception):
    """Exception raised when agent creation fails"""
    pass

# Try to import SDK components, but provide fallbacks
try:
    from agents_sdk import SDKAgent, FunctionTool as SDKFunctionTool
    agents_sdk_imported = True
    logger.info("Agents SDK successfully imported")
except ImportError:
    agents_sdk_imported = False
    logger.warning("Could not import Agents SDK - using direct OpenAI API instead")

class OpenAIAgentsSDK(BaseLLM):
    """
    LLM implementation that uses the OpenAI API with fallbacks for Agents SDK functionality.
    """
    
    def __init__(self):
        # Try to get configuration in order of preference
        if hasattr(global_settings, 'OPENAI_AGENTS_SDK_CONFIG'):
            config = global_settings.OPENAI_AGENTS_SDK_CONFIG
            logger.info("Using OPENAI_AGENTS_SDK_CONFIG")
        elif hasattr(global_settings, 'OPENAI_CONFIG'):
            config = global_settings.OPENAI_CONFIG
            logger.info("Using OPENAI_CONFIG")
        else:
            config = global_settings.llm
            logger.info("Using default LLM config")
        
        # Store the full config object for later use
        self.config = config
        
        super().__init__(
            api_key=config.api_key or os.environ.get("OPENAI_API_KEY", ""),
            model_name=config.model_name,
            model_id=config.model_id,
            temperature=config.temperature,
            max_tokens=config.max_tokens,
            system_prompt=config.system_prompt
        )
        self._initialize_model()
        self.tools = []
        self.mcp_available = False
        
    def _initialize_model(self) -> None:
        """Initialize the OpenAI API client."""
        try:
            # Get API key, organization ID, and project ID from environment or config
            self.api_key = self.api_key or os.environ.get("OPENAI_API_KEY", "")
            self.model_id = self.model_id or os.environ.get("OPENAI_MODEL_ID", "o3-mini")
            self.org_id = os.environ.get("OPENAI_ORG_ID", "")
            
            # Disable telemetry for privacy
            os.environ["OPENAI_AGENTS_TELEMETRY_ENABLED"] = "false"
            
            # Get debug mode from environment variable (defaults to False)
            debug_mode = os.environ.get("OPENAI_DEBUG", "false").lower() == "true"
            
            if not self.api_key:
                raise ValueError("OpenAI API key is required")
            
            # Set environment variables for the Agents SDK to use
            os.environ["OPENAI_API_KEY"] = self.api_key
            if self.org_id:
                os.environ["OPENAI_ORG_ID"] = self.org_id
            
            # Initialize MCP support if available
            # Store the result to know if MCP is available later
            self.mcp_available = MCPAdapter.initialize_mcp_support(self.api_key, self.org_id)
            
            # Headers for the OpenAI client
            default_headers = {}
            if self.org_id:
                default_headers["OpenAI-Organization"] = self.org_id
            
            # Add debugging headers if in debug mode
            if debug_mode:
                default_headers["X-Request-Debug"] = "true"
                default_headers["OpenAI-Debug"] = "true"
                logger.info("OpenAI debug mode is enabled")
            
            # Set up the OpenAI client for direct API access when needed
            self.client = OpenAI(
                api_key=self.api_key,
                default_headers=default_headers
            )
            
            # Set up the async OpenAI client
            self.async_client = AsyncOpenAI(
                api_key=self.api_key,
                default_headers=default_headers
            )
            
            # Initialize tools list
            self.tools = []
            # Initialize MCP tools list if MCP is available
            self.mcp_tools = [] if self.mcp_available else None
            
            # Log all OpenAI environment variables for debugging
            openai_vars = {k: v for k, v in os.environ.items() if 'OPENAI' in k.upper()}
            logger.info(f"OpenAI environment variables: {', '.join(openai_vars.keys())}")
            
            # Log successful initialization
            logger.info(f"Initialized OpenAI client with model: {self.model_id}")
            if self.org_id:
                logger.info(f"Using organization: {self.org_id}")
                
        except Exception as e:
            logger.error(f"Failed to initialize OpenAI client: {str(e)}")
            raise
    
    def _prepare_messages(
        self,
        query: str,
        chat_history: Optional[List[ChatMessage]] = None
    ) -> List[dict]:
        """Convert chat history to the format expected by OpenAI API."""
        messages = []
        
        # Add system message if provided
        if self.system_prompt:
            messages.append({"role": "system", "content": self.system_prompt})
        
        # Add chat history
        if chat_history:
            for msg in chat_history:
                messages.append({"role": msg.role, "content": msg.content})
        
        # Add the user query
        messages.append({"role": "user", "content": query})
        return messages
    
    def _prepare_functions(self) -> List[Dict[str, Any]]:
        """Prepare functions for the OpenAI API."""
        functions = []
        if hasattr(self, 'tools') and self.tools:
            for tool in self.tools:
                if hasattr(tool, 'metadata'):
                    try:
                        # Basic function definition
                        function_def = {
                            "name": tool.metadata.name,
                            "description": tool.metadata.description
                        }
                        
                        # Create a basic parameters schema if needed
                        parameters = {
                            "type": "object",
                            "properties": {},
                            "required": []
                        }
                        
                        # Try to infer parameters from the function signature if available
                        if hasattr(tool, 'fn') and callable(tool.fn):
                            import inspect
                            sig = inspect.signature(tool.fn)
                            
                            # Skip first parameter if it's 'self'
                            params = list(sig.parameters.items())
                            
                            for name, param in params:
                                # Basic type mapping
                                param_type = "string"  # Default to string
                                
                                if param.annotation != inspect.Parameter.empty:
                                    if param.annotation == int:
                                        param_type = "integer"
                                    elif param.annotation == float:
                                        param_type = "number"
                                    elif param.annotation == bool:
                                        param_type = "boolean"
                                
                                # Add to properties
                                parameters["properties"][name] = {
                                    "type": param_type,
                                    "description": f"Parameter: {name}"
                                }
                                
                                # If parameter has no default value, it's required
                                if param.default == inspect.Parameter.empty:
                                    parameters["required"].append(name)
                        
                        # Set the parameters
                        function_def["parameters"] = parameters
                        
                        # Add to functions list
                        functions.append(function_def)
                        logger.info(f"Prepared function: {tool.metadata.name}")
                    except Exception as e:
                        logger.error(f"Error preparing function {tool.metadata.name}: {str(e)}")
        return functions
    
    def _extract_response(self, response: Any) -> str:
        """Extract text content from various response formats."""
        try:
            # For direct OpenAI API responses
            if hasattr(response, 'choices') and response.choices:
                return response.choices[0].message.content or ""
                
            # For string responses
            if isinstance(response, str):
                return response
                
            # For dict responses
            if isinstance(response, dict) and 'content' in response:
                return response['content']
                
            # Fallback to the existing extraction method
            return safe_extract_content(response)
        except Exception as e:
            logger.error(f"Error extracting OpenAI response: {str(e)}")
            return "Error processing response"
    
    def create_agent(self, system_prompt=None, instructions=None, model_to_use=None, agent_id=None, tools_list=None, assisted=False):
        """
        Create a basic agent representation (not an actual agent when SDK is unavailable).
        This is just a placeholder to maintain API compatibility.
        """
        # Generate ID if needed
        if agent_id is None:
            agent_id = f"agent-{str(uuid.uuid4())}"
            
        # Use provided system prompt or fall back to config
        if system_prompt is None:
            system_prompt = self.system_prompt
            
        # Use provided model or fall back to config
        if model_to_use is None:
            model_to_use = self.model_id
            
        # Use provided tools list or use all registered tools
        if tools_list is None and hasattr(self, 'tools'):
            tools_list = self.tools
        
        logger.info(f"Created basic agent config with model {model_to_use} and {len(tools_list) if tools_list else 0} tools")
        
        # Return a simple data object to represent the agent
        return {
            "id": agent_id,
            "model": model_to_use,
            "instructions": instructions or system_prompt,
            "tools": tools_list or []
        }
            
    def _create_agent(self, system_prompt=None, instructions=None, model_to_use=None, agent_id=None, tools_list=None):
        """Legacy method, use create_agent instead"""
        return self.create_agent(
            system_prompt=system_prompt,
            instructions=instructions,
            model_to_use=model_to_use,
            agent_id=agent_id,
            tools_list=tools_list,
            assisted=False
        )
            
    def chat(
        self,
        query: str,
        chat_history: Optional[List[ChatMessage]] = None
    ) -> str:
        """
        Process a query using the OpenAI API.
        
        Args:
            query: The user's query
            chat_history: Optional chat history
            
        Returns:
            String response from the API
        """
        try:
            # Prepare input
            messages = self._prepare_messages(query, chat_history)
            functions = self._prepare_functions()
            
            # For tools-enabled completion, use the functions API
            if functions:
                logger.info(f"Making OpenAI completion with {len(functions)} tools")
                response = self.client.chat.completions.create(
                    model=self.model_id,
                    messages=messages,
                    functions=functions,
                    max_completion_tokens=self.max_tokens
                )
            else:
                # Standard completion without tools
                logger.info("Making standard OpenAI completion without tools")
                response = self.client.chat.completions.create(
                    model=self.model_id,
                    messages=messages,
                    max_completion_tokens=self.max_tokens
                )
            
            return self._extract_response(response)
        except Exception as e:
            logger.error(f"Error in OpenAI chat: {str(e)}")
            return f"I encountered an error processing your request: {str(e)}"
            
    async def achat(
        self,
        query: str,
        chat_history: Optional[List[ChatMessage]] = None
    ) -> str:
        """
        Process a query asynchronously using the OpenAI API.
        
        Args:
            query: The user's query
            chat_history: Optional chat history
            
        Returns:
            String response from the API
        """
        try:
            # Prepare input
            messages = self._prepare_messages(query, chat_history)
            functions = self._prepare_functions()
            
            # For tools-enabled completion, use the functions API
            if functions:
                logger.info(f"Making async OpenAI completion with {len(functions)} tools")
                response = await self.async_client.chat.completions.create(
                    model=self.model_id,
                    messages=messages,
                    functions=functions,
                    max_completion_tokens=self.max_tokens
                )
            else:
                # Standard completion without tools
                logger.info("Making standard async OpenAI completion without tools")
                response = await self.async_client.chat.completions.create(
                    model=self.model_id,
                    messages=messages,
                    max_completion_tokens=self.max_tokens
                )
            
            return self._extract_response(response)
        except Exception as e:
            logger.error(f"Error in OpenAI achat: {str(e)}")
            return f"I encountered an error processing your request: {str(e)}"
    
    def stream_chat(
        self,
        query: str,
        chat_history: Optional[List[ChatMessage]] = None
    ) -> Generator[str, None, None]:
        """
        Stream a response using the OpenAI API.
        
        Args:
            query: The user's query
            chat_history: Optional chat history
            
        Yields:
            Stream of string chunks from the response
        """
        try:
            # Prepare input
            messages = self._prepare_messages(query, chat_history)
            functions = self._prepare_functions()
            
            # For tools-enabled completion, use the functions API with streaming
            if functions:
                logger.info(f"Making streaming OpenAI completion with {len(functions)} tools")
                response = self.client.chat.completions.create(
                    model=self.model_id,
                    messages=messages,
                    functions=functions,
                    max_completion_tokens=self.max_tokens,
                    stream=True
                )
            else:
                # Standard completion without tools
                logger.info("Making standard streaming OpenAI completion without tools")
                response = self.client.chat.completions.create(
                    model=self.model_id,
                    messages=messages,
                    max_completion_tokens=self.max_tokens,
                    stream=True
                )
            
            # Process chunks from the stream
            for chunk in response:
                if hasattr(chunk, 'choices') and chunk.choices:
                    delta = chunk.choices[0].delta
                    if hasattr(delta, 'content') and delta.content:
                        yield delta.content
        except Exception as e:
            logger.error(f"Error in OpenAI stream_chat: {str(e)}")
            yield f"I encountered an error processing your request: {str(e)}"
    
    async def astream_chat(
        self,
        query: str,
        chat_history: Optional[List[ChatMessage]] = None
    ) -> AsyncGenerator[str, None]:
        """
        Stream a response asynchronously using the OpenAI API.
        
        Args:
            query: The user's query
            chat_history: Optional chat history
            
        Yields:
            Asynchronous stream of string chunks from the response
        """
        try:
            # Prepare input
            messages = self._prepare_messages(query, chat_history)
            functions = self._prepare_functions()
            
            # For tools-enabled completion, use the functions API with streaming
            if functions:
                logger.info(f"Making async streaming OpenAI completion with {len(functions)} tools")
                response = await self.async_client.chat.completions.create(
                    model=self.model_id,
                    messages=messages,
                    functions=functions,
                    max_completion_tokens=self.max_tokens,
                    stream=True
                )
            else:
                # Standard completion without tools
                logger.info("Making standard async streaming OpenAI completion without tools")
                response = await self.async_client.chat.completions.create(
                    model=self.model_id,
                    messages=messages,
                    max_completion_tokens=self.max_tokens,
                    stream=True
                )
            
            # Process chunks from the stream
            async for chunk in response:
                if hasattr(chunk, 'choices') and chunk.choices:
                    delta = chunk.choices[0].delta
                    if hasattr(delta, 'content') and delta.content:
                        yield delta.content
        except Exception as e:
            logger.error(f"Error in OpenAI astream_chat: {str(e)}")
            yield f"I encountered an error processing your request: {str(e)}"
    
    @asynccontextmanager
    async def session(self):
        """Context manager for agent session."""
        yield self
    
    def register_tool(self, func, name=None, description=None, schema=None):
        """
        Register a function as a tool for the agent to use.
        
        Args:
            func: The function to register
            name: Optional custom name for the tool
            description: Optional description of what the tool does
            schema: Optional JSON schema for the tool's parameters
            
        Returns:
            True if registration was successful, False otherwise
        """
        try:
            # Make sure we have a tools list
            if not hasattr(self, 'tools'):
                self.tools = []
                
            # Create a FunctionTool from the provided function
            function_tool = FunctionTool.from_defaults(
                fn=func,
                name=name or func.__name__,
                description=description or func.__doc__
            )
            
            # Add the tool to our list of tools
            self.tools.append(function_tool)
            
            # Register with MCP if available
            if hasattr(self, 'mcp_available') and self.mcp_available:
                return self.register_mcp_tool(function_tool, schema)
                
            # Log success
            logger.info(f"Successfully registered tool: {function_tool.metadata.name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to register tool {name or func.__name__}: {str(e)}")
            return False
            
    def register_mcp_tool(self, function_tool, schema=None):
        """
        Register a FunctionTool as an MCP tool for the agent to use.
        If MCP support is not available, register as a regular tool instead.
        
        Args:
            function_tool: The FunctionTool to register
            schema: Optional JSON schema for the tool's parameters
            
        Returns:
            True if registration was successful, False otherwise
        """
        try:
            # Check if MCP support is available
            if not hasattr(self, 'mcp_available') or not self.mcp_available:
                logger.warning("MCP support is not available. Tool will not be registered as MCP tool.")
                
                # Instead, register as a regular tool
                if not hasattr(self, 'tools'):
                    self.tools = []
                
                # Add the tool to our list of regular tools
                if function_tool not in self.tools:
                    self.tools.append(function_tool)
                    logger.info(f"Registered {function_tool.metadata.name} as regular tool (MCP fallback)")
                    return True
                return False
                
            # Initialize MCP tools list if needed
            if not hasattr(self, 'mcp_tools') or self.mcp_tools is None:
                self.mcp_tools = []
                
            # Convert the FunctionTool to MCP format
            mcp_tool = MCPAdapter.convert_to_function_tool(function_tool, schema)
            
            # Add the tool to our list of MCP tools
            if mcp_tool:
                self.mcp_tools.append(mcp_tool)
                logger.info(f"Successfully registered MCP tool: {function_tool.metadata.name}")
                return True
            else:
                logger.warning(f"Failed to convert tool to MCP format: {function_tool.metadata.name}")
                return False
                
        except Exception as e:
            logger.error(f"Failed to register MCP tool {function_tool.metadata.name}: {str(e)}")
            return False 