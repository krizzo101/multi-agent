import asyncio
from contextlib import asynccontextmanager
from typing import AsyncGenerator, Generator, List, Optional
from llama_index.llms.openai import OpenAI as LlamaIndexOpenAI
from llama_index.core.llms import ChatMessage
from .base import BaseLLM
from src.settings import global_settings
from src.agents.utils.pattern import safe_extract_content
import logging
import os
from openai import OpenAI, AsyncOpenAI

logger = logging.getLogger(__name__)

class OpenAILLM(BaseLLM):
    def __init__(self):
        config = global_settings.OPENAI_CONFIG
        super().__init__(
            api_key=config.api_key,
            model_name=config.model_name,
            model_id=config.model_id,
            temperature=config.temperature,
            max_tokens=config.max_tokens,
            system_prompt=config.system_prompt
        )
        self._initialize_model()

    def _initialize_model(self) -> None:
        try:
            # Use the OpenAI client directly
            self.api_key = self.api_key or os.environ.get("OPENAI_API_KEY", "")
            if not self.api_key:
                raise ValueError("OpenAI API key is required")
                
            # Basic configuration for OpenAI client
            self.client = OpenAI(api_key=self.api_key)
            self.async_client = AsyncOpenAI(api_key=self.api_key)
            
            # Log successful initialization
            logger.info(f"Initialized OpenAI client with model: {self.model_id}")
            
        except Exception as e:
            logger.error(f"Failed to initialize OpenAI model: {str(e)}")
            raise

    def _prepare_messages(
        self,
        query: str,
        chat_history: Optional[List[ChatMessage]] = None
    ) -> List[dict]:
        messages = []
        if self.system_prompt:
            messages.append({"role": "system", "content": self.system_prompt})
            messages.append({"role": "assistant", "content": "I understand and will follow these instructions."})
        
        if chat_history:
            for msg in chat_history:
                messages.append({"role": msg.role, "content": msg.content})
        
        messages.append({"role": "user", "content": query})
        return messages

    def _extract_response(self, response) -> str:
        """Extract text from OpenAI response."""
        try:
            if hasattr(response, 'choices') and response.choices:
                return response.choices[0].message.content
            return safe_extract_content(response)
        except Exception as e:
            logger.error(f"Error extracting OpenAI response: {str(e)}")
            return "Error processing response"

    def chat(
        self,
        query: str,
        chat_history: Optional[List[ChatMessage]] = None
    ) -> str:
        try:
            messages = self._prepare_messages(query, chat_history)
            response = self.client.chat.completions.create(
                model=self.model_id,
                messages=messages,
                temperature=self.temperature,
                max_tokens=self.max_tokens,
                top_p=global_settings.OPENAI_CONFIG.top_p
            )
            return self._extract_response(response)
        except Exception as e:
            logger.error(f"Error in OpenAI chat: {str(e)}")
            raise

    async def achat(
        self,
        query: str,
        chat_history: Optional[List[ChatMessage]] = None
    ) -> str:
        try:
            messages = self._prepare_messages(query, chat_history)
            response = await self.async_client.chat.completions.create(
                model=self.model_id,
                messages=messages,
                temperature=self.temperature,
                max_tokens=self.max_tokens,
                top_p=global_settings.OPENAI_CONFIG.top_p
            )
            return self._extract_response(response)
        except Exception as e:
            logger.error(f"Error in OpenAI async chat: {str(e)}")
            raise

    def stream_chat(
        self,
        query: str,
        chat_history: Optional[List[ChatMessage]] = None
    ) -> Generator[str, None, None]:
        try:
            messages = self._prepare_messages(query, chat_history)
            response_stream = self.client.chat.completions.create(
                model=self.model_id,
                messages=messages,
                temperature=self.temperature,
                max_tokens=self.max_tokens,
                top_p=global_settings.OPENAI_CONFIG.top_p,
                stream=True
            )
            for response in response_stream:
                if hasattr(response.choices[0], 'delta') and response.choices[0].delta.content:
                    yield response.choices[0].delta.content
        except Exception as e:
            logger.error(f"Error in OpenAI stream chat: {str(e)}")
            raise

    async def astream_chat(
        self,
        query: str,
        chat_history: Optional[List[ChatMessage]] = None
    ) -> AsyncGenerator[str, None]:
        try:
            messages = self._prepare_messages(query, chat_history)
            response_stream = await self.async_client.chat.completions.create(
                model=self.model_id,
                messages=messages,
                temperature=self.temperature,
                max_tokens=self.max_tokens,
                top_p=global_settings.OPENAI_CONFIG.top_p,
                stream=True
            )
            async for response in response_stream:
                if hasattr(response.choices[0], 'delta') and response.choices[0].delta.content:
                    yield response.choices[0].delta.content
        except Exception as e:
            logger.error(f"Error in OpenAI async stream chat: {str(e)}")
            raise
            
    @asynccontextmanager
    async def session(self):
        """Context manager for managing the session with the model"""
        try:
            yield self
        finally:
            # Cleanup code if needed
            pass
