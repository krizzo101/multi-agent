import logging
from typing import Optional, List

from src.agents import (
    ReflectionAgent,
    PlanningAgent,
    AgentOptions,
    ManagerAgent,
    FallbackAgent
)
from src.tools.tool_manager import weather_tool
from src.agents.llm import GeminiLLM
from llama_index.core.llms import ChatMessage
from src.settings import global_settings

# Get a logger for this module
logger = logging.getLogger(__name__)

class AgentChat:
    def __init__(self):
        # Initialize LLM
        self.llm = GeminiLLM()
        
        # Verbose flag from configuration 
        self.verbose = global_settings.agent.verbose_logging
        
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
        
        # Initialize specialized agents
        self.reflection_agent = ReflectionAgent(
            self.llm,
            AgentOptions(
                id="reflection",
                name="Reflection Assistant",
                description="Helps with information generation and refinement about topics"
            )
        )
        
        self.planning_agent = PlanningAgent(
            self.llm,
            AgentOptions(
                id="planning",
                name="Planning Assistant",
                description="Assists with project planning, task breakdown, and using weather tool"
            ),
            tools=[weather_tool]
        )
        
        # Initialize manager agent
        self.manager = ManagerAgent(
            self.llm,
            AgentOptions(
                id="manager",
                name="Manager",
                description="Routes requests to specialized agents"
            )
        )
        
        # Register agents with manager (including default agent)
        self.manager.register_agent(self.default_agent)
        self.manager.register_agent(self.reflection_agent)
        self.manager.register_agent(self.planning_agent)
        
        # Chat history to provide context
        self.chat_history: List[ChatMessage] = []
        
        logger.info("AgentChat initialization complete")
    
    async def get_response(self, user_input: str, verbose: bool = None) -> str:
        """
        Process user input by routing to appropriate agent
        
        Args:
            user_input (str): User's query
            verbose (bool): Whether to log detailed information (overrides default)
        
        Returns:
            str: Agent's response
        """
        # Use specified verbose flag or default from config
        verbose = self.verbose if verbose is None else verbose
        
        logger.info(f"Processing user input: {user_input[:50]}...")
        
        try:
            # Process the input and get a response
            response = await self.manager.run(
                query=user_input,
                chat_history=self.chat_history,
                verbose=verbose
            )
            
            # Update chat history
            self.chat_history.append(ChatMessage(role="user", content=user_input))
            self.chat_history.append(ChatMessage(role="assistant", content=response))
            
            # Trim chat history to last 10 messages to prevent context overflow
            self.chat_history = self.chat_history[-10:]
            
            logger.info("Response generated successfully")
            return response
        
        except Exception as e:
            logger.error(f"Error in get_response: {str(e)}", exc_info=True)
            return "I'm sorry, I encountered an error processing your request."
    
    def reset_chat(self):
        """Reset the chat history"""
        logger.info("Resetting chat history")
        self.chat_history = []
