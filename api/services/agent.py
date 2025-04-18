import logging
from typing import Optional, List, Dict, Any
import asyncio
import time
import sys
import re
import os

from src.agents import (
    ReflectionAgent,
    PlanningAgent,
    AgentOptions,
    SmartAgentProxy,
    FallbackAgent
)
from src.tools.tool_manager import weather_tool, get_all_tools
from src.tools.brave_search import brave_search_tool
from src.agents.llm import GeminiLLM, OpenAILLM, ClaudeLLM, OpenAIAgentsSDK
from llama_index.core.llms import ChatMessage
from src.settings import global_settings

# Get a logger for this module
logger = logging.getLogger(__name__)

class AgentChat:
    def __init__(self):
        # Check and log environment variables for OpenAI configuration
        openai_api_key = os.environ.get('OPENAI_API_KEY', '')
        openai_model = os.environ.get('OPENAI_MODEL_ID', 'o3-mini')
        openai_org_id = os.environ.get('OPENAI_ORG_ID', '')
        
        if not openai_api_key:
            logger.warning("OPENAI_API_KEY environment variable not set - using default API key")
        if not openai_org_id:
            logger.info("OPENAI_ORG_ID environment variable not set - using default organization")
        
        # Initialize LLM based on environment variable or config
        default_llm = os.environ.get('DEFAULT_LLM', 'gemini').lower()
        
        # Log selected LLM provider
        logger.info(f"Using LLM provider: {default_llm}")
        
        # Flag to determine if we should use the Agents SDK path
        self.use_agents_sdk = False
        
        if default_llm == 'openai':
            try:
                # Try to use the OpenAI Agents SDK
                logger.info("Initializing with OpenAI Agents SDK")
                self.llm = OpenAIAgentsSDK()
                self.use_agents_sdk = True
            except Exception as e:
                # Fall back to the standard OpenAI client if the SDK fails
                logger.warning(f"Failed to initialize OpenAI Agents SDK, falling back to standard client: {str(e)}")
                self.llm = OpenAILLM()
        elif default_llm == 'claude':
            logger.info("Initializing with Claude LLM")
            self.llm = ClaudeLLM()
        else:
            logger.info("Initializing with Gemini LLM")
            self.llm = GeminiLLM()
        
        # Verbose flag from configuration 
        self.verbose = global_settings.agent.verbose_logging
        
        # Response timeout in seconds - use getattr instead of .get method
        self.response_timeout = getattr(global_settings.agent, "response_timeout", 30)
        
        logger.info("Initializing AgentChat with agents")
        
        # Create a default agent for fallback
        self.default_agent = FallbackAgent(
            self.llm,
            AgentOptions(
                id="default",
                name="Default Assistant",
                description="Provides general conversational assistance"
            )
        )
        
        # Get all available tools
        all_tools = get_all_tools()
        
        # Initialize specialized agents
        self.reflection_agent = ReflectionAgent(
            self.llm,
            AgentOptions(
                id="reflection",
                name="Reflection Assistant",
                description="Helps with information generation and refinement about topics"
            ),
            tools=[brave_search_tool]  # Add search tool to reflection agent
        )
        
        self.planning_agent = PlanningAgent(
            self.llm,
            AgentOptions(
                id="planning",
                name="Planning Assistant",
                description="Assists with project planning, task breakdown, and using weather tool"
            ),
            tools=all_tools  # Give planning agent access to all tools
        )
        
        # Initialize Smart Agent Proxy
        self.proxy = SmartAgentProxy(
            self.llm,
            AgentOptions(
                id="proxy",
                name="Smart Agent Proxy",
                description="Intelligently routes requests to specialized agents with context tracking"
            ),
            response_timeout=self.response_timeout
        )
        
        # Register agents with proxy
        self.proxy.register_agent(self.default_agent)
        self.proxy.register_agent(self.reflection_agent)
        self.proxy.register_agent(self.planning_agent)
        
        # Define patterns for simplified routing
        self.routing_patterns = {
            r'(?i)plan|task|weather|schedule|organize|project': 'planning',
            r'(?i)history|information|topic|learn|explain|tell me about|what is|who is|search|find': 'reflection',
        }
        
        logger.info("AgentChat initialization complete")
        
        # Register tools with the Agents SDK if available
        if self.use_agents_sdk and hasattr(self.llm, 'register_tool'):
            self._register_sdk_tools()
    
    def _register_sdk_tools(self):
        """Register available tools with the OpenAI Agents SDK."""
        try:
            # Safer checking for configuration values
            tools_enabled = True  # Default to enabled
            
            # Check if weather tool should be registered (default to false)
            weather_enabled = False
            
            # Try to access configuration safely
            try:
                if hasattr(global_settings, 'tools'):
                    tools_enabled = getattr(global_settings.tools, "enabled", True)
                    if hasattr(global_settings.tools, 'weather'):
                        weather_enabled = getattr(global_settings.tools.weather, "enabled", False)
            except AttributeError:
                # Config structure doesn't match expected format, use defaults
                logger.info("Using default tool settings (no tools configuration found)")
            
            if not tools_enabled:
                logger.info("Tool registration is disabled in configuration")
                return
                
            # Register specific tools based on configuration
            registered_tools = 0
            
            # Register the weather tool if enabled
            if weather_enabled and hasattr(weather_tool, 'fn'):
                result = self.llm.register_tool(weather_tool.fn)
                if result:
                    registered_tools += 1
                    logger.info("Registered weather tool with OpenAI Agents SDK")
                else:
                    logger.info("Weather tool registration failed")
            else:
                logger.info("Weather tool is disabled or unavailable")
                
            # Register Brave Search tool - try MCP first, fall back to regular if needed
            if hasattr(self.llm, 'register_mcp_tool'):
                result = self.llm.register_mcp_tool(brave_search_tool)
                if result:
                    registered_tools += 1
                    logger.info("Registered Brave Search tool with OpenAI Agents SDK")
                else:
                    # Fall back to regular registration if MCP registration failed
                    result = self.llm.register_tool(brave_search_tool.fn)
                    if result:
                        registered_tools += 1
                        logger.info("Registered Brave Search as regular tool (MCP fallback)")
                    else:
                        logger.warning("Failed to register Brave Search tool")
            else:
                # Fall back to regular registration if MCP registration is not available
                result = self.llm.register_tool(brave_search_tool.fn)
                if result:
                    registered_tools += 1
                    logger.info("Registered Brave Search as regular tool")
                else:
                    logger.warning("Failed to register Brave Search tool")
            
            # Log the total number of tools registered
            tool_count = len(getattr(self.llm, 'tools', []))
            if hasattr(self.llm, 'mcp_tools') and self.llm.mcp_tools is not None:
                tool_count += len(self.llm.mcp_tools)
            logger.info(f"Total tools registered with OpenAI Agents SDK: {tool_count}")
            
        except Exception as e:
            logger.warning(f"Failed to register tools with Agents SDK: {str(e)}")
            logger.exception(e)
    
    def _classify_query(self, query: str, session_id: str = None) -> tuple:
        """Simple rule-based classification to determine which agent to use
        
        Args:
            query: User's query text
            session_id: Optional session ID to check conversation history
            
        Returns:
            Tuple of (agent_id, confidence)
        """
        # Check for follow-up context if session exists
        if session_id and session_id in self.proxy.sessions:
            context = self.proxy.sessions[session_id]
            
            # If this is a follow-up, use the same agent
            if context.current_agent_id and context.metadata["turn_count"] > 0:
                # Simple follow-up detection for keywords
                follow_up_patterns = [
                    r'(?i)^(yes|no|maybe|ok|okay|sure|thanks|correct|right|exactly|continue|proceed|go on)',
                    r'(?i)^(tell me more|what about|how about|and|also|additionally)',
                    r'(?i)^(why|how|when|where|who|what|which)'
                ]
                
                for pattern in follow_up_patterns:
                    if re.search(pattern, query.strip()):
                        logger.info(f"Detected follow-up, continuing with agent: {context.current_agent_id}")
                        return context.current_agent_id, 0.9
        
        # Pattern-based routing for new queries
        for pattern, agent_id in self.routing_patterns.items():
            if re.search(pattern, query):
                logger.info(f"Matched pattern for {agent_id} agent: {pattern}")
                return agent_id, 0.8
                
        # Default to the default agent
        return "default", 0.6
    
    async def _process_with_agents_sdk(
        self, 
        user_input: str, 
        user_id: str = "", 
        session_id: str = "", 
        verbose: bool = None
    ) -> str:
        """
        Process user input directly using the OpenAI Agents SDK.
        
        Args:
            user_input: User's query
            user_id: Optional user identifier
            session_id: Optional session identifier
            verbose: Whether to log detailed information
            
        Returns:
            Agent's response
        """
        start_time = time.time()
        logger.info(f"Processing with Agents SDK: {user_input[:50]}...")
        
        try:
            # Get or create session context
            context = self.proxy._get_or_create_session(session_id, user_id)
            
            # Add user message to context
            context.add_user_message(user_input)
            
            # Provide chat history to the SDK if needed
            chat_history = context.get_recent_history()
            
            # Process with a timeout
            try:
                # Using asyncio.shield to prevent cancellation during important operations
                response_task = asyncio.shield(self.llm.achat(
                    query=user_input,
                    chat_history=chat_history
                ))
                
                # Apply timeout
                response = await asyncio.wait_for(response_task, timeout=self.response_timeout)
                
                elapsed = time.time() - start_time
                logger.info(f"Agents SDK processing completed in {elapsed:.2f} seconds")
                
                # Validate response
                if not response or not isinstance(response, str):
                    logger.warning(f"Invalid response type from Agents SDK: {type(response)}")
                    response = "I'm sorry, the system generated an invalid response. Please try again."
                
                # Add response to context
                context.add_assistant_message(response)
                
                return response
                
            except asyncio.TimeoutError:
                elapsed = time.time() - start_time
                logger.warning(f"Agents SDK processing timed out after {elapsed:.2f} seconds (limit: {self.response_timeout}s)")
                
                timeout_msg = f"I'm sorry, but it's taking longer than expected to process your request (over {self.response_timeout} seconds). Please try a simpler query or try again later."
                context.add_assistant_message(timeout_msg)
                
                return timeout_msg
                
            except asyncio.CancelledError:
                elapsed = time.time() - start_time
                logger.warning(f"Agents SDK processing was cancelled after {elapsed:.2f} seconds")
                
                cancel_msg = "I'm sorry, your request was cancelled. Please try again."
                context.add_assistant_message(cancel_msg)
                
                return cancel_msg
                
        except Exception as e:
            elapsed = time.time() - start_time
            logger.error(f"Error in Agents SDK processing after {elapsed:.2f}s: {str(e)}", exc_info=True)
            
            error_msg = "I'm sorry, I encountered an error processing your request. Please try again or rephrase your question."
            
            # Try to add to conversation context
            if 'context' in locals() and context:
                context.add_assistant_message(error_msg)
                
            return error_msg
    
    async def get_response(self, user_input: str, user_id: str = "", session_id: str = "", verbose: bool = None) -> str:
        """
        Process user input by routing to appropriate agent via the Smart Agent Proxy
        
        Args:
            user_input (str): User's query
            user_id (str): Optional user identifier
            session_id (str): Optional session identifier
            verbose (bool): Whether to log detailed information (overrides default)
        
        Returns:
            str: Agent's response
        """
        # If using Agents SDK, use the direct processing path
        if self.use_agents_sdk and hasattr(self.llm, 'achat'):
            return await self._process_with_agents_sdk(user_input, user_id, session_id, verbose)
        
        # Otherwise, use the traditional processing path
        # Use specified verbose flag or default from config
        verbose = self.verbose if verbose is None else verbose
        
        start_time = time.time()
        logger.info(f"Processing user input: {user_input[:50]}...")
        
        try:
            # Get or create session context
            context = self.proxy._get_or_create_session(session_id, user_id)
            
            # Add user message to context
            context.add_user_message(user_input)
            
            # Simple classification
            agent_id, confidence = self._classify_query(user_input, session_id)
            
            # Get the agent
            agent = self.proxy.agent_registry.get(agent_id, self.default_agent)
            
            # Update context with the selected agent
            context.update_agent(agent.id, confidence)
            
            # Low confidence response
            if confidence < 0.6:
                clarification_msg = (
                    f"I'm not entirely sure I understand your request. "
                    f"I think {agent.name} might be able to help, "
                    f"but could you please provide more details about what you need?"
                )
                context.add_assistant_message(clarification_msg)
                return clarification_msg
            
            # Process the input with a timeout to prevent hanging
            try:
                # Using asyncio.shield to prevent cancellation during important operations
                response_task = asyncio.shield(agent.run(
                    query=user_input,
                    verbose=verbose,
                    context={"conversation_stage": "understanding" if context.metadata["turn_count"] <= 1 else "continuation"},
                    user_id=user_id,
                    session_id=session_id,
                    chat_history=context.get_recent_history()
                ))
                
                # Apply timeout - cancel if taking too long
                response = await asyncio.wait_for(response_task, timeout=self.response_timeout)
                
                elapsed = time.time() - start_time
                logger.info(f"Agent processing completed in {elapsed:.2f} seconds")
                
                # Validate response
                if not response or not isinstance(response, str):
                    logger.warning(f"Invalid response type: {type(response)}")
                    response = "I'm sorry, the system generated an invalid response. Please try again."
                
                # Add response to context
                context.add_assistant_message(response)
                
                return response
                
            except asyncio.TimeoutError:
                elapsed = time.time() - start_time
                logger.warning(f"Agent processing timed out after {elapsed:.2f} seconds (limit: {self.response_timeout}s)")
                
                timeout_msg = f"I'm sorry, but it's taking longer than expected to process your request (over {self.response_timeout} seconds). Please try a simpler query or try again later."
                context.add_assistant_message(timeout_msg)
                
                return timeout_msg
            
            except asyncio.CancelledError:
                elapsed = time.time() - start_time
                logger.warning(f"Agent processing was cancelled after {elapsed:.2f} seconds")
                
                cancel_msg = "I'm sorry, your request was cancelled. Please try again."
                context.add_assistant_message(cancel_msg)
                
                return cancel_msg
            
        except Exception as e:
            elapsed = time.time() - start_time
            logger.error(f"Error in get_response after {elapsed:.2f}s: {str(e)}", exc_info=True)
            
            error_msg = "I'm sorry, I encountered an error processing your request. Please try again or rephrase your question."
            
            # Try to add to conversation context
            if 'context' in locals() and context:
                context.add_assistant_message(error_msg)
                
            return error_msg
    
    def reset_chat(self, session_id: str = None):
        """Reset the chat history for a specific session or all sessions if no session_id provided"""
        logger.info(f"Resetting chat history for session: {session_id or 'all'}")
        
        if session_id:
            # Remove specific session
            if session_id in self.proxy.sessions:
                del self.proxy.sessions[session_id]
                logger.info(f"Session {session_id} reset successfully")
            else:
                logger.warning(f"Session {session_id} not found")
        else:
            # Reset all sessions
            self.proxy.sessions.clear()
            logger.info("All sessions reset successfully")
            
    async def get_agent_status(self) -> dict:
        """Get status information about the agent system"""
        return await self.proxy.get_agent_status()
