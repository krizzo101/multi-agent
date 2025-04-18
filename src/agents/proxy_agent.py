"""
Smart Agent Proxy implementation for the Multi-Agent System.

This module implements the Smart Agent Proxy layer that provides:
1. Intelligent routing between specialized agents
2. Context tracking and conversation memory
3. An abstraction layer between UIs and agent implementations
4. Dynamic agent selection based on query analysis
5. Fallback handling and graceful error recovery
"""

import logging
import asyncio
import time
import json
from typing import Dict, List, Any, Optional, Tuple, Set
import uuid

from src.agents.base import BaseAgent, AgentOptions
from src.agents.llm import BaseLLM
from src.prompt import get_prompt
from llama_index.core.llms import ChatMessage
from src.agents.utils import clean_json_response

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
        self.current_agent_id: Optional[str] = None
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
        
    def add_message(self, message: ChatMessage) -> None:
        """Add a message to the conversation history.
        
        Args:
            message: Message to add to history
        """
        self.history.append(message)
        self.metadata["turn_count"] += 1
        self.metadata["last_updated"] = time.time()
        
        # Keep history at a reasonable size
        if len(self.history) > 20:
            self.history = self.history[-20:]
    
    def add_user_message(self, content: str) -> None:
        """Add a user message to the conversation history.
        
        Args:
            content: User message content
        """
        self.add_message(ChatMessage(role="user", content=content))
    
    def add_assistant_message(self, content: str) -> None:
        """Add an assistant message to the conversation history.
        
        Args:
            content: Assistant message content
        """
        self.add_message(ChatMessage(role="assistant", content=content))
    
    def update_agent(self, agent_id: str, confidence: float) -> None:
        """Update the current agent and track in history.
        
        Args:
            agent_id: ID of the selected agent
            confidence: Confidence score for the selection
        """
        self.current_agent_id = agent_id
        self.metadata["agent_history"].append(agent_id)
        self.metadata["confidence_scores"].append(confidence)
        
        # Keep agent history at a reasonable size
        if len(self.metadata["agent_history"]) > 20:
            self.metadata["agent_history"] = self.metadata["agent_history"][-20:]
            self.metadata["confidence_scores"] = self.metadata["confidence_scores"][-20:]
    
    def get_recent_history(self, max_items: int = 5) -> List[ChatMessage]:
        """Get the most recent conversation history.
        
        Args:
            max_items: Maximum number of items to return
            
        Returns:
            List of recent chat messages
        """
        return self.history[-max_items:] if self.history else []
        
    def get_formatted_history(self, max_items: int = 5) -> str:
        """Get formatted conversation history for prompts.
        
        Args:
            max_items: Maximum number of items to include
            
        Returns:
            Formatted conversation history as string
        """
        recent = self.get_recent_history(max_items)
        if not recent:
            return "No conversation history available."
            
        formatted = []
        for msg in recent:
            formatted.append(f"{msg.role}: {msg.content}")
        
        return "\n".join(formatted)
    
    def extract_topics_and_entities(self, llm: BaseLLM) -> None:
        """Extract topics and entities from conversation history.
        
        Args:
            llm: LLM instance to use for extraction
        """
        # Only extract if we have enough history
        if len(self.history) < 2:
            return
            
        # TODO: Implement topic/entity extraction using LLM

    def get_last_agent(self) -> Optional[str]:
        """Get the ID of the last agent used in this conversation.
        
        Returns:
            Agent ID or None if no agent has been used
        """
        if not self.metadata["agent_history"]:
            return None
            
        return self.metadata["agent_history"][-1]


class SmartAgentProxy(BaseAgent):
    """Smart Agent Proxy that intelligently routes queries to specialized agents."""
    
    def __init__(
        self,
        llm: BaseLLM,
        options: AgentOptions,
        response_timeout: float = 30.0
    ):
        """Initialize the Smart Agent Proxy.
        
        Args:
            llm: LLM instance for the proxy
            options: Agent options
            response_timeout: Timeout for agent responses in seconds
        """
        super().__init__(llm, options)
        self.agent_registry: Dict[str, BaseAgent] = {}
        self.response_timeout = response_timeout
        self.default_agent_id = "default"  # Default agent ID to use as fallback
        
        # Session contexts
        self.sessions: Dict[str, ConversationContext] = {}
        
        # Performance tracking
        self.performance_metrics: Dict[str, Dict[str, Any]] = {}
        
        logger.info(f"Initialized Smart Agent Proxy with timeout {response_timeout}s")
    
    def register_agent(self, agent: BaseAgent) -> None:
        """Register a specialized agent with the proxy.
        
        Args:
            agent: Agent to register
        """
        self.agent_registry[agent.id] = agent
        
        # Initialize performance tracking for this agent
        self.performance_metrics[agent.id] = {
            "total_calls": 0,
            "successful_calls": 0,
            "error_calls": 0,
            "timeout_calls": 0,
            "avg_response_time": 0,
            "total_response_time": 0
        }
        
        logger.info(f"Registered agent: {agent.id} ({agent.name})")
    
    def _get_agent_descriptions(self) -> str:
        """Get formatted descriptions of all registered agents.
        
        Returns:
            Formatted string with agent descriptions
        """
        descriptions = []
        for agent_id, agent in self.agent_registry.items():
            descriptions.append(f"- {agent.name} (ID: {agent_id}): {agent.description}")
        return "\n".join(descriptions)
    
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
        """Analyze the user query to extract intent and entities.
        
        Args:
            query: User query
            context: Conversation context
            
        Returns:
            Dict with analysis results including intent and entities
        """
        try:
            # Template variables for analysis
            variables = {
                "query": query,
                "chat_history": context.get_formatted_history()
            }
            
            # Get analysis prompt from template system
            analysis_prompt = get_prompt("agent.proxy.analyze", variables)
            
            # Fallback to hardcoded prompt if template not found
            if not analysis_prompt or analysis_prompt.startswith("ERROR:"):
                analysis_prompt = f"""
                Analyze this query to determine the primary intent, key entities, and whether it's a follow-up question.
                
                User query: {query}
                
                Recent conversation:
                {context.get_formatted_history()}
                
                Return a JSON response with these fields:
                - primary_intent: The main intent of the query
                - entities: List of key entities mentioned
                - is_followup: Boolean indicating if this is a follow-up question
                - topic: The general topic area
                - requires_clarification: Boolean indicating if clarification is needed
                - confidence: Confidence score from 0.0 to 1.0
                """
            
            # Get analysis from LLM
            analysis_result = await self.llm.achat(analysis_prompt)
            
            # Extract JSON response
            analysis = clean_json_response(analysis_result)
            
            # Parse JSON
            if isinstance(analysis, str):
                try:
                    analysis = json.loads(analysis)
                except json.JSONDecodeError:
                    logger.error(f"Failed to parse analysis JSON: {analysis}")
                    # Return default values
                    return {
                        "primary_intent": "general",
                        "entities": [],
                        "is_followup": False,
                        "topic": "unknown",
                        "requires_clarification": False,
                        "confidence": 0.5
                    }
            
            logger.info(f"Query analysis: {str(analysis)}")
            return analysis
            
        except Exception as e:
            logger.error(f"Error in query analysis: {str(e)}", exc_info=True)
            # Return default values
            return {
                "primary_intent": "general",
                "entities": [],
                "is_followup": False,
                "topic": "unknown",
                "requires_clarification": False,
                "confidence": 0.5
            }

    async def _select_agent(self, query: str, intent: str, context: ConversationContext) -> Tuple[str, float]:
        """Select the most appropriate agent for the query.
        
        Args:
            query: User query
            intent: Query intent from analysis
            context: Conversation context
            
        Returns:
            Tuple of (agent_id, confidence_score)
        """
        try:
            # Prepare agent descriptions for the LLM
            agent_descriptions = "\n".join([
                f"- {agent_id}: {agent.name} - {agent.description}"
                for agent_id, agent in self.agent_registry.items()
            ])
            
            # Template variables
            variables = {
                "agent_descriptions": agent_descriptions,
                "user_input": query,
                "intent": intent,
                "chat_history": context.get_formatted_history()
            }
            
            # Get classification prompt from template system
            classification_prompt = get_prompt("agent.proxy.classify", variables)
            
            # Fallback to hardcoded prompt if template not found
            if not classification_prompt or classification_prompt.startswith("ERROR:"):
                classification_prompt = f"""
                You are AgentMatcher, an intelligent assistant designed to analyze user queries and match them with 
                the most suitable agent. Your task is to understand the user request,
                identify key entities and intents, and determine which agent would be best equipped
                to handle the query.
                
                Available agents and their capabilities:
                {agent_descriptions}
                
                Based on the user input and context, determine the most appropriate agent and provide a confidence score (0-1).
                
                Intent identified: {intent}
                
                Respond in JSON format:
                {{
                    "selected_agent": "agent_id",
                    "confidence": 0.0,
                    "reasoning": "brief explanation"
                }}
                
                User input: {query}
                Recent chat history: {context.get_formatted_history()}
                """
            
            # Get classification from LLM
            response = await self.llm.achat(classification_prompt)
            
            # Clean and parse JSON
            response = clean_json_response(response)
            if isinstance(response, str):
                try:
                    response = json.loads(response)
                except json.JSONDecodeError:
                    logger.error(f"Failed to parse classification JSON: {response}")
                    return self.default_agent_id, 0.5
            
            selected_agent = response.get("selected_agent", self.default_agent_id)
            confidence = float(response.get("confidence", 0.5))
            
            # Ensure agent exists, fallback to default if not
            if selected_agent not in self.agent_registry:
                logger.warning(f"Selected agent {selected_agent} not found, using default")
                selected_agent = self.default_agent_id
                confidence = 0.5
            
            logger.info(f"Selected agent: {selected_agent} with confidence: {confidence}")
            return selected_agent, confidence
            
        except Exception as e:
            logger.error(f"Error in agent selection: {str(e)}", exc_info=True)
            return self.default_agent_id, 0.5
    
    async def run(
        self,
        query: str,
        user_id: str = "",
        session_id: str = "",
        verbose: bool = False,
        context: Dict[str, Any] = None,
        additional_params: Dict[str, Any] = {}
    ) -> str:
        """Process user request by intelligently routing to appropriate agent."""
        try:
            # Get or create conversation context for this session
            conv_context = self._get_or_create_session(session_id, user_id)
            
            # Add user message to context
            conv_context.add_user_message(query)
            
            # Parse the query first to extract intents and entities
            try:
                query_analysis = await self._analyze_query(query, conv_context)
                intent = query_analysis.get("primary_intent", "general")
                is_followup = query_analysis.get("is_followup", False)
                requires_clarification = query_analysis.get("requires_clarification", False)
                
                logger.info(f"Query analysis: intent={intent}, followup={is_followup}, clarification={requires_clarification}")
            except Exception as e:
                logger.error(f"Error during query analysis: {str(e)}", exc_info=True)
                # Use fallback values if analysis fails
                intent = "general"
                is_followup = False
                requires_clarification = False
                
            # Check if we're handling a followup in an existing conversation
            recent_agent_id = conv_context.get_last_agent()
            if is_followup and recent_agent_id and recent_agent_id in self.agent_registry:
                # Route to the same agent that handled the previous query
                selected_agent = self.agent_registry[recent_agent_id]
                confidence = 0.9  # High confidence for followups to same agent
                
                # Update context with agent selection
                conv_context.update_agent(selected_agent.id, confidence)
                
                logger.info(f"Followup detected, routing to previous agent: {selected_agent.id}")
            else:
                # Select the appropriate agent based on intent and other factors
                agent_id, confidence = await self._select_agent(query, intent, conv_context)
                selected_agent = self.agent_registry.get(agent_id, self.agent_registry.get("default"))
                
                # If confidence is too low, maybe we need clarification
                if confidence < 0.6 or requires_clarification:
                    clarification_response = (
                        f"I'm not entirely sure what you're asking about. "
                        f"I think {selected_agent.name} might be able to help, "
                        f"but could you please provide more details about what you need?"
                    )
                    
                    # Record the clarification in context
                    conv_context.update_agent(selected_agent.id, confidence)
                    conv_context.add_assistant_message(clarification_response)
                    
                    return clarification_response
                
                # Update context with agent selection
                conv_context.update_agent(selected_agent.id, confidence)
            
            # Track metrics
            self.performance_metrics[selected_agent.id]["total_calls"] += 1
            
            # Setup context for the agent
            agent_context = {
                "conversation_stage": "understanding" if conv_context.metadata["turn_count"] <= 1 else "continuation",
                "intent": intent,
                "is_followup": is_followup
            }
            
            # Add any additional context from the original call
            if context:
                agent_context.update(context)
            
            # Process the request with the selected agent
            try:
                # Pass required parameters to the agent
                start_time = time.time()
                agent_response = await selected_agent.run(
                    query=query,
                    verbose=verbose,
                    context=agent_context,
                    user_id=user_id,
                    session_id=session_id,
                    chat_history=conv_context.get_recent_history(),
                    **additional_params
                )
                elapsed = time.time() - start_time
                logger.info(f"Agent {selected_agent.id} response time: {elapsed:.2f}s")
                
                # Validate the response - handle unexpected formats from LLMs
                if not isinstance(agent_response, str):
                    if hasattr(agent_response, 'content'):
                        # Try to extract content field
                        agent_response = str(agent_response.content)
                    elif hasattr(agent_response, 'finish_reason') and agent_response.finish_reason == 'RECITATION':
                        # Handle citation metadata responses
                        agent_response = "I found some information about this topic, but cannot display it with proper citations. Please try rephrasing your question."
                    else:
                        # Convert to string for any other type
                        agent_response = str(agent_response)
                
                # Record the response in context
                conv_context.add_assistant_message(agent_response)
                
                # Update metrics for the agent
                self.performance_metrics[selected_agent.id]["success_calls"] += 1
                
                return agent_response
                
            except Exception as agent_error:
                logger.error(f"Error with agent {selected_agent.id}: {str(agent_error)}", exc_info=True)
                self.performance_metrics[selected_agent.id]["error_calls"] += 1
                
                error_message = (
                    f"I'm sorry, but {selected_agent.name} encountered an error while processing your request. "
                    f"Please try again or rephrase your question."
                )
                
                # Record the error in context
                conv_context.add_assistant_message(error_message)
                
                return error_message
                
        except Exception as e:
            logger.error(f"Error in Smart Agent Proxy: {str(e)}", exc_info=True)
            
            # Try to track the error if we know the agent
            if 'selected_agent' in locals() and selected_agent and selected_agent.id in self.performance_metrics:
                self.performance_metrics[selected_agent.id]["error_calls"] += 1
            
            error_msg = (
                "I encountered an error while processing your request. "
                "Please try again or rephrase your question."
            )
            
            # Try to add to conversation context if available
            if 'conv_context' in locals() and conv_context:
                conv_context.add_assistant_message(error_msg)
                
            return error_msg
    
    async def get_agent_status(self) -> Dict[str, Any]:
        """Get status information about all registered agents.
        
        Returns:
            Dictionary with agent status information
        """
        return {
            "total_agents": len(self.agent_registry),
            "registered_agents": [
                {
                    "id": agent_id,
                    "name": agent.name,
                    "description": agent.description,
                    "performance": self.performance_metrics.get(agent_id, {})
                }
                for agent_id, agent in self.agent_registry.items()
            ],
            "active_sessions": len(self.sessions)
        } 