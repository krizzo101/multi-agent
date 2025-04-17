from abc import ABC, abstractmethod
from contextlib import asynccontextmanager
from typing import Any, AsyncGenerator, Generator, List, Optional
from llama_index.core.llms import ChatMessage
from llama_index.llms.anthropic import Anthropic
from llama_index.llms.gemini import Gemini
from llama_index.llms.openai import OpenAI
from src.settings import global_settings
import logging

logger = logging.getLogger(__name__)

class BaseLLM(ABC):
    def __init__(
        self, 
        api_key: str = None, 
        model_name: str = None, 
        model_id: str = None, 
        temperature: float = None, 
        max_tokens: int = None, 
        system_prompt: str = None
    ):
        """
        Initialize base LLM class.

        Args:
            api_key (str): API key for the model
            model_name (str): Name of the model
            model_id (str): ID of the model
            temperature (float): Temperature for text generation
            max_tokens (int): Maximum number of tokens for each response
            system_prompt (str): Default system prompt
        """
        self.api_key = api_key
        self.model_name = model_name
        self.model_id = model_id
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.system_prompt = system_prompt

    def _get_openai_config(self):
        """Helper method to create OpenAI configuration"""
        config = {
            'api_key': self.api_key if self.api_key else global_settings.llm.api_key,
            'model': self.model_id if self.model_id else global_settings.llm.model_id,
            'temperature': self.temperature if self.temperature else global_settings.llm.temperature,
            'max_tokens': self.max_tokens if self.max_tokens else global_settings.llm.max_tokens,
        }
        
        # Add optional endpoint configuration if provided
        endpoint_cfg = global_settings.llm.endpoint_config
        if endpoint_cfg.api_base:
            config['api_base'] = endpoint_cfg.api_base
        if endpoint_cfg.organization_id:
            config['organization_id'] = endpoint_cfg.organization_id
        if endpoint_cfg.api_version:
            config['api_version'] = endpoint_cfg.api_version
            
        # Add additional parameters
        config['top_p'] = global_settings.llm.top_p
        config['frequency_penalty'] = global_settings.llm.frequency_penalty
        config['presence_penalty'] = global_settings.llm.presence_penalty
        
        return config

    def _initialize_model(self) -> None:
        try:
            # Handle OpenAI models - both standard and small models
            if (self.model_name.lower() in global_settings.OPENAI_MODEL_TYPES or 
                self.model_name in global_settings.OPENAI_SMALL_MODELS):
                config = self._get_openai_config()
                self.model = OpenAI(**config)
            
            # Handle Gemini models
            elif self.model_name.lower() in global_settings.GEMINI_MODEL_TYPES:
                # Use the explicit GEMINI_CONFIG that was added to the Config instance
                self.model = Gemini(
                    api_key=self.api_key if self.api_key else global_settings.GEMINI_CONFIG.api_key,
                    model=self.model_id if self.model_id else global_settings.GEMINI_CONFIG.model_id,
                    temperature=self.temperature if self.temperature else global_settings.GEMINI_CONFIG.temperature,
                    max_tokens=self.max_tokens if self.max_tokens else global_settings.GEMINI_CONFIG.max_tokens,
                    additional_kwargs={
                        'generation_config': {
                            'temperature': self.temperature if self.temperature else global_settings.GEMINI_CONFIG.temperature,
                            'top_p': global_settings.GEMINI_CONFIG.top_p,
                            'top_k': global_settings.GEMINI_CONFIG.top_k,
                        }
                    },
                    api_base=global_settings.GEMINI_CONFIG.endpoint_config.api_base if global_settings.GEMINI_CONFIG.endpoint_config.api_base else None,
                    api_version=global_settings.GEMINI_CONFIG.endpoint_config.api_version if global_settings.GEMINI_CONFIG.endpoint_config.api_version else None,
                )
            
            # Handle Claude/Anthropic models
            elif self.model_name.lower() in global_settings.CLAUDE_MODEL_TYPES:
                # Use the explicit CLAUDE_CONFIG that was added to the Config instance
                self.model = Anthropic(
                    api_key=self.api_key if self.api_key else global_settings.CLAUDE_CONFIG.api_key,
                    model=self.model_id if self.model_id else global_settings.CLAUDE_CONFIG.model_id,
                    temperature=self.temperature if self.temperature else global_settings.CLAUDE_CONFIG.temperature,
                    max_tokens=self.max_tokens if self.max_tokens else global_settings.CLAUDE_CONFIG.max_tokens,
                    top_p=global_settings.CLAUDE_CONFIG.top_p,
                    api_base=global_settings.CLAUDE_CONFIG.endpoint_config.api_base if global_settings.CLAUDE_CONFIG.endpoint_config.api_base else None,
                    api_version=global_settings.CLAUDE_CONFIG.endpoint_config.api_version if global_settings.CLAUDE_CONFIG.endpoint_config.api_version else None,
                )
            else:
                raise ValueError(f"Unsupported model type: {self.model_name}")
                
        except Exception as e:
            logger.error(f"Failed to initialize {self.model_name} model: {str(e)}")
            raise

    @abstractmethod
    def _prepare_messages(
        self, 
        query: str, 
        chat_history: Optional[List[ChatMessage]] = None
    ) -> List[ChatMessage]:
        pass
    
    def _extract_response(self, response: Any):
        """
        Extract content from various response formats.
        
        Args:
            response: The response object from the LLM
            
        Returns:
            str: The extracted content
        """
        try:
            if hasattr(response, 'content'):
                return response.content
            elif hasattr(response, 'message') and hasattr(response.message, 'content'):
                return response.message.content
            elif isinstance(response, dict) and 'content' in response:
                return response['content']
            elif isinstance(response, str):
                return response
            else:
                # Try best effort to get string representation
                return str(response)
        except Exception as e:
            logger.error(f"Error extracting response from {self.model_name}: {str(e)}")
            return response.message.content
        
    @abstractmethod
    def chat(
        self, 
        query: str, 
        chat_history: Optional[List[ChatMessage]] = None
    ) -> str:
        pass

    @abstractmethod
    async def achat(
        self, 
        query: str, 
        chat_history: Optional[List[ChatMessage]] = None
    ) -> str:
        pass

    @abstractmethod
    def stream_chat(
        self, 
        query: str, 
        chat_history: Optional[List[ChatMessage]] = None
    ) -> Generator[str, None, None]:
        pass

    @abstractmethod
    async def astream_chat(
        self, 
        query: str, 
        chat_history: Optional[List[ChatMessage]] = None
    ) -> AsyncGenerator[str, None]:
        pass
    
    def get_model_name(self) -> str:
        return self.model_name

    def get_model_config(self) -> dict:
        return {
            "model_name": self.model_name,
            "model_id": self.model_id,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "system_prompt": self.system_prompt
        }
    @asynccontextmanager
    async def session(self):
        try:
            yield self
        finally:
            # Cleanup code if needed
            pass