"""
Dynamic Agent Proxy implementation for Multi-Agent System.

This module implements a Dynamic Agent Proxy that analyzes user queries
and dynamically creates optimized agent configurations on the fly, rather
than selecting from a predefined set of agents.
"""

import logging
import asyncio
import time
import json
import uuid
import re
from typing import Dict, List, Any, Optional, Tuple

from src.agents.base import BaseAgent, AgentOptions
from src.agents.llm import BaseLLM
from src.prompt import get_prompt
from llama_index.core.llms import ChatMessage
from src.agents.utils import (
    clean_json_response, 
    get_template_manager, 
    QueryAnalyzer
)

logger = logging.getLogger(__name__)

class ConversationContext:
    """Class for tracking and managing conversation context."""
    
    def __init__(self, session_id: str = None, user_id: str = None):
        """Initialize conversation context with optional session and user IDs.
        
        Args:
            session_id: Unique session identifier
            user_id: User identifier
        """
        self.session_id = session_id or str(uuid.uuid4())
        self.user_id = user_id or "anonymous"
        self.current_agent_config: Optional[Dict[str, Any]] = None
        self.history: List[ChatMessage] = []
        self.metadata: Dict[str, Any] = {
            "topics": [],
            "entities": [],
            "intents": [],
            "created_at": time.time(),
            "last_updated": time.time(),
            "turn_count": 0,
            "agent_history": [],
            "confidence_scores": []
        }
        
    def add_user_message(self, message: str) -> None:
        """Add a user message to the conversation history.
        
        Args:
            message: User message content
        """
        self.history.append(ChatMessage(role="user", content=message))
        self.metadata["turn_count"] += 1
        self.metadata["last_updated"] = time.time()
        
    def add_assistant_message(self, message: str) -> None:
        """Add an assistant message to the conversation history.
        
        Args:
            message: Assistant message content
        """
        self.history.append(ChatMessage(role="assistant", content=message))
        self.metadata["last_updated"] = time.time()
        
    def get_formatted_history(self, max_turns: int = 5) -> str:
        """Get the conversation history formatted as a string.
        
        Args:
            max_turns: Maximum number of conversation turns to include
            
        Returns:
            Formatted conversation history as a string
        """
        formatted = []
        # Limit to the last max_turns * 2 messages (user + assistant)
        recent_messages = self.history[-max_turns*2:] if len(self.history) > max_turns*2 else self.history
        
        for msg in recent_messages:
            role = "User" if msg.role == "user" else "Assistant"
            formatted.append(f"{role}: {msg.content}")
            
        return "\n".join(formatted)
    
    def get_recent_history(self, max_turns: int = 5) -> List[ChatMessage]:
        """Get the recent conversation history.
        
        Args:
            max_turns: Maximum number of conversation turns to include
            
        Returns:
            List of recent ChatMessage objects
        """
        # Limit to the last max_turns * 2 messages (user + assistant)
        return self.history[-max_turns*2:] if len(self.history) > max_turns*2 else self.history
        
    def update_agent_config(self, agent_config: Dict[str, Any], confidence: float = 1.0) -> None:
        """Update the current agent configuration.
        
        Args:
            agent_config: New agent configuration
            confidence: Confidence score for this configuration
        """
        # Store the previous config in history if it exists
        if self.current_agent_config:
            self.metadata["agent_history"].append(self.current_agent_config)
            
        # Update to the new configuration
        self.current_agent_config = agent_config
        self.metadata["confidence_scores"].append(confidence)
        self.metadata["last_updated"] = time.time()
        
    def get_last_agent_config(self) -> Optional[Dict[str, Any]]:
        """Get the most recent agent configuration.
        
        Returns:
            Most recent agent configuration or None if no history
        """
        if self.current_agent_config:
            return self.current_agent_config
        elif self.metadata["agent_history"]:
            return self.metadata["agent_history"][-1]
        return None


class DynamicAgentProxy(BaseAgent):
    """
    Dynamic Agent Proxy that generates custom agent configurations
    on the fly based on user queries, instead of selecting from 
    predefined agents.
    """
    
    def __init__(
        self,
        llm: BaseLLM,
        options: AgentOptions,
        response_timeout: float = 30.0
    ):
        """Initialize the Dynamic Agent Proxy.
        
        Args:
            llm: LLM instance for the proxy
            options: Agent options
            response_timeout: Timeout for agent responses in seconds
        """
        super().__init__(llm, options)
        self.response_timeout = response_timeout
        
        # Session contexts
        self.sessions: Dict[str, ConversationContext] = {}
        
        # Performance tracking
        self.performance_metrics: Dict[str, Dict[str, Any]] = {
            "total_calls": 0,
            "successful_calls": 0,
            "error_calls": 0,
            "timeout_calls": 0,
            "avg_response_time": 0,
            "total_response_time": 0,
            "dynamic_configurations_created": 0
        }
        
        logger.info(f"Initialized Dynamic Agent Proxy with timeout {response_timeout}s")
    
    def _get_or_create_session(self, session_id: str = "", user_id: str = "") -> ConversationContext:
        """Get or create a new conversation context for the given session.
        
        Args:
            session_id: Session identifier
            user_id: User identifier
            
        Returns:
            ConversationContext: Session context
        """
        if not session_id:
            # Generate a new session ID if none provided
            session_id = f"session_{len(self.sessions) + 1}"
            
        # Create a new session if needed
        if session_id not in self.sessions:
            self.sessions[session_id] = ConversationContext(
                session_id=session_id,
                user_id=user_id
            )
            
        return self.sessions[session_id]
    
    async def _analyze_query(self, query: str, context: ConversationContext) -> Dict[str, Any]:
        """Analyze the query to determine intent, topics, and other metadata.
        
        Args:
            query: User query
            context: Conversation context
            
        Returns:
            Analysis results including intent, topics, etc.
        """
        try:
            # First try using the QueryAnalyzer utility
            query_analyzer = QueryAnalyzer()
            
            # Get conversation history in a format suitable for analysis
            conversation_history = []
            for msg in context.history:
                conversation_history.append({
                    "role": msg.role,
                    "content": msg.content
                })
                
            # Use the analyzer for initial analysis
            analysis = query_analyzer.analyze_query(query, conversation_history)
            
            # For more complex analysis, augment with LLM
            if analysis.get("complexity", 0) >= 3:
                # Prepare template variables
                variables = {
                    "user_input": query,
                    "chat_history": context.get_formatted_history(),
                    "initial_analysis": json.dumps(analysis, indent=2)
                }
                
                # Get analysis prompt from template system
                analysis_prompt = get_prompt("agent.proxy.analyze", variables)
                
                # Fallback to hardcoded prompt if template not found
                if not analysis_prompt or analysis_prompt.startswith("ERROR:"):
                    analysis_prompt = f"""
                    You are QueryAnalyzer, an expert at understanding user queries and extracting structured information.
                    Analyze the following user query in the context of the conversation and extract:
                    
                    1. Primary intent (what the user is trying to accomplish)
                    2. Topics and domains mentioned or implied
                    3. Whether this appears to be a follow-up to previous conversation
                    4. Key entities mentioned (people, technologies, concepts, etc.)
                    5. Complexity level (1-5, where 1 is simple and 5 is very complex)
                    6. Required expertise areas to answer this query optimally
                    
                    Initial analysis:
                    {json.dumps(analysis, indent=2)}
                    
                    User query: {query}
                    
                    Recent conversation history: 
                    {context.get_formatted_history()}
                    
                    Respond in JSON format:
                    {{
                        "primary_intent": "string",
                        "topics": ["string", "string"],
                        "domains": ["string", "string"],
                        "is_followup": true/false,
                        "entities": ["string", "string"],
                        "complexity": int,
                        "required_expertise": ["string", "string"],
                        "reasoning": "string"
                    }}
                    """
                
                # Get enhanced analysis from LLM
                response = await self.llm.achat(analysis_prompt)
                
                # Clean and parse JSON
                response = clean_json_response(response)
                try:
                    llm_analysis = json.loads(response)
                    
                    # Merge LLM analysis with initial analysis, preferring LLM results
                    for key, value in llm_analysis.items():
                        analysis[key] = value
                        
                except json.JSONDecodeError:
                    logger.warning(f"Failed to parse LLM analysis JSON, using initial analysis only")
            
            # Update context metadata with analysis
            context.metadata["topics"] = analysis.get("topics", [])
            context.metadata["entities"] = analysis.get("entities", [])
            context.metadata["intents"] = [analysis.get("primary_intent")] + context.metadata["intents"]
            
            logger.info(f"Query analysis: intent={analysis.get('primary_intent')}, followup={analysis.get('is_followup')}")
            return analysis
                
        except Exception as e:
            logger.error(f"Error during query analysis: {str(e)}", exc_info=True)
            # Use fallback values if analysis fails
            return {
                "primary_intent": "general",
                "is_followup": len(context.history) > 0,
                "topics": [],
                "domains": [],
                "entities": [],
                "complexity": 3,
                "required_expertise": ["general"]
            }
    
    async def _generate_agent_config(self, query: str, analysis: Dict[str, Any], context: ConversationContext) -> Dict[str, Any]:
        """Generate a custom agent configuration optimized for the query.
        
        Args:
            query: User query
            analysis: Query analysis results
            context: Conversation context
            
        Returns:
            Dynamic agent configuration
        """
        try:
            # First, check if we can use a pre-defined template
            template_manager = get_template_manager()

            # Look for cached config for similar query
            cached_config = template_manager.get_cached_config(query, context.session_id)
            if cached_config:
                logger.info(f"Using cached agent configuration for similar query")
                return cached_config

            # Find best template match based on analysis
            template_id, customization_vars = template_manager.find_best_template(analysis)
            
            # Add query-specific customization variables
            customization_vars["task_description"] = query
            
            # Add any additional instructions from the analysis
            if "additional_instructions" not in customization_vars:
                required_expertise = ", ".join(analysis.get("required_expertise", []))
                if required_expertise:
                    customization_vars["additional_instructions"] = f"Focus on your expertise in {required_expertise} for this query."
                    
            # Customize the template
            config = template_manager.customize_template(template_id, customization_vars)
            
            if config:
                logger.info(f"Generated agent configuration from template '{template_id}'")
                # Cache the configuration
                template_manager.cache_config(query, config, context.session_id)
                return config
                
            # If template-based approach fails, fall back to LLM-based generation
            logger.warning(f"Template customization failed, falling back to LLM-based generation")
                
            # Prepare template variables
            variables = {
                "user_input": query,
                "chat_history": context.get_formatted_history(),
                "query_analysis": json.dumps(analysis, indent=2)
            }
            
            # Get configuration prompt from template system
            config_prompt = get_prompt("agent.proxy.configure", variables)
            
            # Fallback to hardcoded prompt if template not found
            if not config_prompt or config_prompt.startswith("ERROR:"):
                config_prompt = f"""
                You are AgentConfigurator, an expert at creating optimal agent configurations tailored to specific queries.
                
                Based on the user's query and the query analysis, design an expert agent configuration that is perfectly suited to address the user's needs.
                
                User query: {query}
                
                Query analysis: 
                {json.dumps(analysis, indent=2)}
                
                Recent conversation history: 
                {context.get_formatted_history()}
                
                Create a configuration that specifies:
                1. The agent's specialization and expertise profile
                2. The system message that should be used to instruct the agent
                3. Temperature setting (0.0-1.0) appropriate for this query
                4. Any additional context the agent should have
                
                Respond in JSON format:
                {{
                    "agent_id": "dynamic_<descriptive_id>",
                    "name": "string",
                    "description": "string",
                    "expertise_areas": ["string", "string"],
                    "system_message": "string",
                    "temperature": float,
                    "prompt_preamble": "string",
                    "additional_context": {{}}
                }}
                
                Guidelines:
                - Make the system_message specific, detailed, and tailored to the query's domain
                - Keep temperature low (0.1-0.3) for factual/technical questions, higher (0.4-0.7) for creative tasks
                - Create an agent profile that would be best suited for this specific query
                - The prompt_preamble should frame the user's query optimally for the agent
                """
            
            # Get configuration from LLM
            response = await self.llm.achat(config_prompt)
            
            # Clean and parse JSON
            response = clean_json_response(response)
            try:
                config = json.loads(response)
                
                # Generate a unique ID if not provided or invalid
                if not config.get("agent_id") or not re.match(r"^[a-zA-Z0-9_-]+$", config.get("agent_id", "")):
                    config["agent_id"] = f"dynamic_{int(time.time())}"
                
                # Ensure required fields exist
                if not config.get("name"):
                    config["name"] = f"Dynamic Agent for {analysis.get('primary_intent', 'general query')}"
                    
                if not config.get("description"):
                    config["description"] = f"Specialized agent for {', '.join(analysis.get('required_expertise', ['general']))}"
                    
                if not config.get("system_message"):
                    config["system_message"] = "You are a helpful assistant."
                    
                # Validate temperature
                if "temperature" not in config or not isinstance(config["temperature"], (int, float)):
                    config["temperature"] = 0.5
                else:
                    config["temperature"] = min(max(0.0, float(config["temperature"])), 1.0)
                
                # Add timestamp
                config["created_at"] = time.time()
                    
                logger.info(f"Generated dynamic agent configuration: {config['name']}")
                self.performance_metrics["dynamic_configurations_created"] += 1
                
                # Cache this configuration
                template_manager.cache_config(query, config, context.session_id)
                
                return config
                
            except json.JSONDecodeError:
                logger.error(f"Failed to parse configuration JSON: {response}")
                return self._create_fallback_config(analysis)
                
        except Exception as e:
            logger.error(f"Error during agent configuration: {str(e)}", exc_info=True)
            return self._create_fallback_config(analysis)
    
    def _create_fallback_config(self, analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Create a fallback agent configuration when dynamic generation fails.
        
        Args:
            analysis: Query analysis results
            
        Returns:
            Fallback agent configuration
        """
        # Create a simple config based on available information
        expertise = analysis.get("required_expertise", ["general"])
        expertise_str = ", ".join(expertise)
        
        return {
            "agent_id": f"fallback_{int(time.time())}",
            "name": f"General Assistant",
            "description": f"Assistant with knowledge of {expertise_str}",
            "expertise_areas": expertise,
            "system_message": f"You are a helpful assistant with expertise in {expertise_str}. Provide accurate and concise answers to the user's questions.",
            "temperature": 0.5,
            "prompt_preamble": "",
            "additional_context": {},
            "created_at": time.time()
        }
    
    async def _evolve_agent_config(
        self, 
        query: str, 
        previous_config: Dict[str, Any], 
        analysis: Dict[str, Any], 
        context: ConversationContext
    ) -> Dict[str, Any]:
        """Evolve an existing agent configuration based on new query.
        
        Args:
            query: User query
            previous_config: Previous agent configuration
            analysis: Query analysis results
            context: Conversation context
            
        Returns:
            Updated agent configuration
        """
        # If not a follow-up or very different domain, create new config
        if not analysis.get("is_followup", False):
            return await self._generate_agent_config(query, analysis, context)
            
        try:
            # Get the template manager
            template_manager = get_template_manager()
            
            # Get cached config if available
            cached_config = template_manager.get_cached_config(query, context.session_id)
            if cached_config:
                logger.info(f"Using cached agent configuration for similar query")
                return cached_config
            
            # If the previous config was template-based, we can try to reuse it
            if "template_id" in previous_config and previous_config["template_id"] in template_manager.templates:
                template_id = previous_config["template_id"]
                
                # Build customization variables
                customization_vars = {}
                # Carry over specialization and expertise areas
                if "specialization" in previous_config:
                    customization_vars["specialization"] = previous_config["specialization"]
                
                # Add new task description
                customization_vars["task_description"] = query
                
                # Get compatible tools for this template
                customization_vars["tools"] = template_manager.get_compatible_tools(template_id)
                
                # Customize the template
                config = template_manager.customize_template(template_id, customization_vars)
                
                if config:
                    logger.info(f"Evolved agent configuration from template '{template_id}'")
                    # Add evolution metadata
                    config["evolved_from"] = previous_config.get("agent_id")
                    config["evolution_reason"] = "Follow-up query using same template"
                    config["created_at"] = time.time()
                    
                    # Cache the configuration
                    template_manager.cache_config(query, config, context.session_id)
                    return config
            
            # If template-based approach fails, fall back to LLM-based evolution
            logger.info(f"Template evolution failed, falling back to LLM-based evolution")
            
            # Prepare template variables
            variables = {
                "user_input": query,
                "chat_history": context.get_formatted_history(),
                "query_analysis": json.dumps(analysis, indent=2),
                "previous_config": json.dumps(previous_config, indent=2)
            }
            
            # Get evolution prompt from template system
            evolution_prompt = get_prompt("agent.proxy.evolve", variables)
            
            # Fallback to hardcoded prompt if template not found
            if not evolution_prompt or evolution_prompt.startswith("ERROR:"):
                evolution_prompt = f"""
                You are AgentEvolver, an expert at adapting agent configurations to evolving conversations.
                
                The user's conversation has progressed, and you need to decide whether to keep the current agent configuration,
                modify it, or create an entirely new one.
                
                User's new query: {query}
                
                Query analysis: 
                {json.dumps(analysis, indent=2)}
                
                Current agent configuration:
                {json.dumps(previous_config, indent=2)}
                
                Recent conversation history: 
                {context.get_formatted_history()}
                
                Decide whether to:
                1. KEEP the existing configuration (if it's still optimal)
                2. MODIFY the existing configuration (if minor changes are needed)
                3. REPLACE with a new configuration (if a significant change in direction)
                
                Respond in JSON format:
                {{
                    "decision": "KEEP|MODIFY|REPLACE",
                    "reasoning": "string",
                    "modified_config": {{
                        // Only include if decision is MODIFY or REPLACE
                        "agent_id": "string",
                        "name": "string",
                        "description": "string",
                        "expertise_areas": ["string"],
                        "system_message": "string",
                        "temperature": float,
                        "prompt_preamble": "string",
                        "additional_context": {{}}
                    }}
                }}
                """
            
            # Get evolution decision from LLM
            response = await self.llm.achat(evolution_prompt)
            
            # Clean and parse JSON
            response = clean_json_response(response)
            try:
                result = json.loads(response)
                decision = result.get("decision", "KEEP").upper()
                
                if decision == "KEEP":
                    logger.info("Evolution decision: Keeping existing agent configuration")
                    return previous_config
                    
                elif decision == "MODIFY" or decision == "REPLACE":
                    # Use the new configuration
                    new_config = result.get("modified_config", {})
                    
                    # Ensure required fields exist and are valid
                    if not new_config.get("agent_id"):
                        new_config["agent_id"] = f"{previous_config['agent_id']}_evolved_{int(time.time())}"
                        
                    if not new_config.get("name"):
                        new_config["name"] = previous_config.get("name", "Evolved Agent")
                        
                    if not new_config.get("system_message"):
                        new_config["system_message"] = previous_config.get("system_message", "You are a helpful assistant.")
                        
                    # Validate temperature
                    if "temperature" not in new_config or not isinstance(new_config["temperature"], (int, float)):
                        new_config["temperature"] = previous_config.get("temperature", 0.5)
                    else:
                        new_config["temperature"] = min(max(0.0, float(new_config["temperature"])), 1.0)
                    
                    # Add evolution metadata
                    new_config["evolved_from"] = previous_config.get("agent_id")
                    new_config["evolution_reason"] = result.get("reasoning")
                    new_config["created_at"] = time.time()
                    
                    logger.info(f"Evolution decision: {decision} - Created evolved configuration: {new_config.get('name')}")
                    self.performance_metrics["dynamic_configurations_created"] += 1
                    
                    # Cache the evolved configuration
                    template_manager.cache_config(query, new_config, context.session_id)
                    
                    return new_config
                    
                else:
                    logger.warning(f"Unknown evolution decision: {decision}, falling back to existing config")
                    return previous_config
                    
            except json.JSONDecodeError:
                logger.error(f"Failed to parse evolution JSON: {response}")
                return previous_config
                
        except Exception as e:
            logger.error(f"Error during agent evolution: {str(e)}", exc_info=True)
            return previous_config
    
    async def _process_with_dynamic_agent(
        self, 
        query: str, 
        agent_config: Dict[str, Any], 
        context: ConversationContext,
        **kwargs
    ) -> str:
        """Process a query using a dynamically configured agent.
        
        Args:
            query: User query
            agent_config: Dynamic agent configuration
            context: Conversation context
            kwargs: Additional arguments
            
        Returns:
            Agent response
        """
        try:
            # Prepare the complete system message with any prompt preamble
            system_message = agent_config.get("system_message", "You are a helpful assistant.")
            prompt_preamble = agent_config.get("prompt_preamble", "")
            
            # Add tool-specific instructions to system message
            tools = agent_config.get("tools", [])
            if tools:
                tool_manager = get_template_manager()
                
                # Add tool instructions to system message
                for tool_id in tools:
                    tool_config = tool_manager.get_tool_config(tool_id)
                    if tool_config and "system_prompt_addition" in tool_config:
                        system_message += f"\n\n{tool_config['system_prompt_addition']}"
                
                # Adjust temperature based on tools if needed
                temperature_adjustment = 0.0
                for tool_id in tools:
                    tool_config = tool_manager.get_tool_config(tool_id)
                    if tool_config and "temperature_adjustment" in tool_config:
                        temperature_adjustment += float(tool_config["temperature_adjustment"])
                
                # Apply temperature adjustment
                base_temperature = agent_config.get("temperature", 0.5)
                adjusted_temperature = max(0.0, min(1.0, base_temperature + temperature_adjustment))
                
                # Update configuration with adjusted temperature
                if abs(adjusted_temperature - base_temperature) > 0.01:
                    logger.info(f"Adjusted temperature from {base_temperature:.2f} to {adjusted_temperature:.2f} based on tools")
                    agent_config["temperature"] = adjusted_temperature
            
            # Combine the system message and any preamble with the user query
            effective_prompt = query
            if prompt_preamble:
                effective_prompt = f"{prompt_preamble}\n\n{query}"
                
            # Configure the LLM with the dynamic agent's settings
            temperature = agent_config.get("temperature", 0.5)
            
            # Get recent chat history
            chat_history = context.get_recent_history()
            
            # Add the system message to the context
            if chat_history and len(chat_history) > 0:
                # Check if we need to replace an existing system message
                if chat_history[0].role == "system":
                    chat_history[0] = ChatMessage(role="system", content=system_message)
                else:
                    # Insert system message at the beginning
                    chat_history.insert(0, ChatMessage(role="system", content=system_message))
            else:
                # Create new history with system message
                chat_history = [ChatMessage(role="system", content=system_message)]
            
            # Process with the LLM, using the dynamic configuration
            start_time = time.time()
            
            response = await self.llm.achat(
                query=effective_prompt,
                chat_history=chat_history[:-1],  # Exclude the latest user message which is in effective_prompt
                temperature=temperature
            )
            
            elapsed_time = time.time() - start_time
            
            # Update performance metrics
            self.performance_metrics["total_calls"] += 1
            self.performance_metrics["successful_calls"] += 1
            self.performance_metrics["total_response_time"] += elapsed_time
            self.performance_metrics["avg_response_time"] = (
                self.performance_metrics["total_response_time"] / 
                self.performance_metrics["total_calls"]
            )
            
            logger.info(f"Dynamic agent response generated in {elapsed_time:.2f}s using {len(tools)} tools")
            return response
            
        except asyncio.TimeoutError:
            self.performance_metrics["timeout_calls"] += 1
            logger.warning(f"Dynamic agent processing timed out after {self.response_timeout}s")
            return f"I'm sorry, but it's taking me longer than expected to answer your question. Please try asking a simpler question."
            
        except Exception as e:
            self.performance_metrics["error_calls"] += 1
            logger.error(f"Error in dynamic agent processing: {str(e)}", exc_info=True)
            return f"I'm sorry, but I encountered an error processing your request. Please try again or rephrase your question."
    
    async def run(
        self,
        query: str,
        user_id: str = "",
        session_id: str = "",
        verbose: bool = False,
        context: Dict[str, Any] = None,
        **kwargs
    ) -> str:
        """Process a query with the Dynamic Agent Proxy.
        
        Args:
            query: User query
            user_id: User identifier
            session_id: Session identifier
            verbose: Enable verbose logging
            context: Additional context
            kwargs: Additional arguments
            
        Returns:
            Response from the dynamically configured agent
        """
        start_time = time.time()
        logger.info(f"Dynamic Agent Proxy processing: {query[:50]}...")
        
        try:
            # Get or create conversation context
            conv_context = self._get_or_create_session(session_id, user_id)
            
            # Add user message to context
            conv_context.add_user_message(query)
            
            # 1. Analyze the query
            query_analysis = await self._analyze_query(query, conv_context)
            
            # 2. Check for existing agent configuration
            previous_config = conv_context.get_last_agent_config()
            
            # 3. Create or evolve agent configuration
            if previous_config and query_analysis.get("is_followup", False):
                # Evolve the existing configuration
                agent_config = await self._evolve_agent_config(query, previous_config, query_analysis, conv_context)
            else:
                # Generate a new configuration
                agent_config = await self._generate_agent_config(query, query_analysis, conv_context)
            
            # 4. Update the context with the selected/created configuration
            conv_context.update_agent_config(agent_config)
            
            # 5. Process the query with the dynamic agent
            response = await self._process_with_dynamic_agent(query, agent_config, conv_context, **kwargs)
            
            # 6. Add response to conversation context
            conv_context.add_assistant_message(response)
            
            elapsed_time = time.time() - start_time
            logger.info(f"Dynamic Agent Proxy completed in {elapsed_time:.2f}s")
            
            return response
            
        except Exception as e:
            elapsed_time = time.time() - start_time
            logger.error(f"Error in Dynamic Agent Proxy run(): {str(e)}", exc_info=True)
            
            error_msg = "I encountered an error processing your request. Please try again or rephrase your question."
            
            # Try to add to conversation context
            if 'conv_context' in locals():
                conv_context.add_assistant_message(error_msg)
                
            return error_msg
    
    async def get_agent_status(self) -> Dict[str, Any]:
        """Get status information about the dynamic agent system.
        
        Returns:
            Status information and metrics
        """
        # Count active sessions
        active_sessions = 0
        for session_id, session in self.sessions.items():
            # Consider a session active if it's been updated in the last hour
            if time.time() - session.metadata["last_updated"] < 3600:
                active_sessions += 1
                
        return {
            "agent_type": "DynamicAgentProxy",
            "name": self.name,
            "active_sessions": active_sessions,
            "total_sessions": len(self.sessions),
            "performance_metrics": self.performance_metrics,
            "uptime": time.time() - self.metadata.get("created_at", time.time())
        } 