from abc import ABC, abstractmethod
from dataclasses import dataclass, field
import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Union
from src.agents.llm import BaseLLM
from llama_index.core.llms import ChatMessage
from src.prompt import get_prompt, get_prompt_for_scenario

# Base Types and Data Classes
class AgentType(Enum):
    DEFAULT = "DEFAULT"
    CODING = "CODING"
    PLANNING = "PLANNING"
    REFLECTION = "REFLECTION"

@dataclass
class AgentProcessingResult:
    user_input: str
    agent_id: str
    agent_name: str
    user_id: str
    session_id: str
    additional_params: Dict[str, Any] = field(default_factory=dict)

@dataclass
class AgentResponse:
    metadata: AgentProcessingResult
    output: Union[Any, str]
    streaming: bool
    
class AgentCallbacks:
    def on_llm_new_token(self, token: str) -> None:
        pass
    
    def on_agent_start(self, agent_name: str) -> None:
        pass
    
    def on_agent_end(self, agent_name: str) -> None:
        pass

@dataclass
class AgentOptions:
    name: str
    description: str
    id: Optional[str] = None
    region: Optional[str] = None
    save_chat: bool = True
    callbacks: Optional[AgentCallbacks] = None
    prompt_template_id: Optional[str] = None
    
@dataclass
class Message:
    role: str
    content: List[Dict[str, str]]
    timestamp: datetime = field(default_factory=datetime.datetime.now)
    
class BaseAgent(ABC):
    """Abstract base class for all agents"""
    
    def __init__(self, llm: BaseLLM, options: AgentOptions):
        self.llm = llm
        self.name = options.name
        self.description = options.description
        self.id = options.id or self.generate_key_from_name(options.name)
        self.region = options.region
        self.save_chat = options.save_chat
        self.callbacks = options.callbacks or AgentCallbacks()
        self.prompt_template_id = options.prompt_template_id
        
    @staticmethod
    def generate_key_from_name(name: str) -> str:
        import re
        # Remove special characters and replace spaces with hyphens
        key = re.sub(r'[^a-zA-Z\s-]', '', name)
        key = re.sub(r'\s+', '-', key)
        return key.lower()
        
    def _create_system_message(self, prompt: str) -> ChatMessage:
        """Create a system message with the given prompt"""
        return ChatMessage(role="system", content=prompt)
    
    def get_prompt(self, template_id: str, variables: Dict[str, Any] = None) -> str:
        """Get a prompt template with variables substituted.
        
        Args:
            template_id: Template identifier
            variables: Variables to substitute in the template
            
        Returns:
            Rendered prompt template
        """
        return get_prompt(template_id, variables or {})
    
    def get_prompt_for_context(self, context: Dict[str, Any], variables: Dict[str, Any] = None) -> Optional[str]:
        """Get a prompt template based on the current context.
        
        Args:
            context: Context information (e.g., conversation stage, intent)
            variables: Variables to substitute in the template
            
        Returns:
            Rendered prompt template or None if no suitable template found
        """
        # If this agent has a specific template ID, use it first
        if self.prompt_template_id:
            try:
                merged_vars = {**context, **(variables or {})}
                return get_prompt(self.prompt_template_id, merged_vars)
            except Exception:
                # If that fails, fall back to scenario detection
                pass
                
        # Use scenario-based detection
        return get_prompt_for_scenario(context, variables)
    
    @abstractmethod
    async def run(
        self,
        query: str,
        verbose: bool = False,
        context: Dict[str, Any] = None,
        *args,
        **kwargs
    ) -> Any:
        """Main execution method that must be implemented by all agents
        
        Args:
            query: User query or task
            verbose: Whether to enable verbose logging
            context: Context information for prompt selection
            
        Returns:
            Agent response
        """
        pass
        
    def is_streaming_enabled(self) -> bool:
        return False
        
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass