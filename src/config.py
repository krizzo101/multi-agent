from dataclasses import dataclass
from pydantic import BaseModel, Field
import dotenv 
dotenv.load_dotenv()
import os
from src.prompt import (LLM_SYSTEM_PROMPT)

# LLM Provider Settings
class LLMEndpointConfig(BaseModel):
    """Configuration for LLM API endpoints and provider settings"""
    api_base: str = ""  # API base URL
    organization_id: str = ""  # Organization ID (for OpenAI, etc.)
    api_version: str = ""  # API version
    deployment_id: str = ""  # Deployment ID (for Azure, etc.)
    timeout: int = 60  # Request timeout

# LLM Configuration
class LLMConfig(BaseModel):
    api_key: str
    model_name: str
    model_id: str
    temperature: float = 0.7
    max_tokens: int = 2048
    system_prompt: str = "You are a helpful assistant."
    # Additional parameters for LLM generation
    top_p: float = Field(default=1.0)
    top_k: int = Field(default=40)
    frequency_penalty: float = Field(default=0.0)
    presence_penalty: float = Field(default=0.0)
    stop_sequences: list = Field(default_factory=list)
    # Provider-specific endpoint config
    endpoint_config: LLMEndpointConfig = Field(default_factory=LLMEndpointConfig)

# Agent Configuration
class AgentConfig(BaseModel):
    save_chat: bool = True
    verbose_logging: bool = False
    max_retries: int = 3
    timeout_seconds: int = 60

# API Configuration
class APIConfig(BaseModel):
    host: str = Field(default="0.0.0.0")
    port: int = Field(default=8000)
    debug: bool = Field(default=False)
    reload: bool = Field(default=True)
    
# UI Configuration
class UIConfig(BaseModel):
    port: int = Field(default=8501)
    address: str = Field(default="0.0.0.0")
    theme: str = Field(default="light")

# Logging Configuration
class LoggingConfig(BaseModel):
    level: str = Field(default="INFO")
    format: str = Field(default="%(asctime)s | %(levelname)-8s - [%(relpathname)s %(funcName)s(%(lineno)d)] - %(message)s")
    log_to_file: bool = Field(default=True)
    log_dir: str = Field(default="logs")

class Config:
    # LLM Configurations
    OPENAI_CONFIG = LLMConfig(
        api_key=os.environ.get('OPENAI_API_KEY', ''),
        model_name="GPT",
        model_id=os.environ.get('OPENAI_MODEL_ID', 'gpt-3.5-turbo'),
        temperature=float(os.environ.get('OPENAI_TEMPERATURE', '0.7')),
        max_tokens=int(os.environ.get('OPENAI_MAX_TOKENS', '2048')),
        system_prompt=LLM_SYSTEM_PROMPT,
        top_p=float(os.environ.get('OPENAI_TOP_P', '1.0')),
        top_k=int(os.environ.get('OPENAI_TOP_K', '40')),
        frequency_penalty=float(os.environ.get('OPENAI_FREQUENCY_PENALTY', '0.0')),
        presence_penalty=float(os.environ.get('OPENAI_PRESENCE_PENALTY', '0.0')),
        endpoint_config=LLMEndpointConfig(
            api_base=os.environ.get('OPENAI_API_BASE', ''),
            organization_id=os.environ.get('OPENAI_ORGANIZATION_ID', ''),
            api_version=os.environ.get('OPENAI_API_VERSION', '')
        )
    )

    GEMINI_CONFIG = LLMConfig(
        api_key=os.environ.get('GOOGLE_API_KEY', ''),
        model_name="Gemini",
        model_id=os.environ.get('GEMINI_MODEL_ID', 'models/gemini-1.5-flash'),
        temperature=float(os.environ.get('GEMINI_TEMPERATURE', '0.8')),
        max_tokens=int(os.environ.get('GEMINI_MAX_TOKENS', '2048')),
        system_prompt=LLM_SYSTEM_PROMPT,
        top_p=float(os.environ.get('GEMINI_TOP_P', '0.8')),
        top_k=int(os.environ.get('GEMINI_TOP_K', '40')),
        endpoint_config=LLMEndpointConfig(
            api_base=os.environ.get('GEMINI_API_BASE', ''),
            api_version=os.environ.get('GEMINI_API_VERSION', '')
        )
    )
    
    CLAUDE_CONFIG = LLMConfig(
        api_key=os.environ.get('ANTHROPIC_API_KEY', ''),
        model_name="Claude",
        model_id=os.environ.get('CLAUDE_MODEL_ID', 'claude-3-haiku-20240307'),
        temperature=float(os.environ.get('CLAUDE_TEMPERATURE', '0.7')),
        max_tokens=int(os.environ.get('CLAUDE_MAX_TOKENS', '4000')),
        system_prompt=LLM_SYSTEM_PROMPT,
        top_p=float(os.environ.get('CLAUDE_TOP_P', '1.0')),
        endpoint_config=LLMEndpointConfig(
            api_base=os.environ.get('ANTHROPIC_API_BASE', ''),
            api_version=os.environ.get('ANTHROPIC_API_VERSION', '')
        )
    )
    
    # Agent Configuration
    AGENT_CONFIG = AgentConfig(
        save_chat=os.environ.get('SAVE_CHAT', 'True').lower() == 'true',
        verbose_logging=os.environ.get('VERBOSE_LOGGING', 'False').lower() == 'true',
        max_retries=int(os.environ.get('MAX_RETRIES', '3')),
        timeout_seconds=int(os.environ.get('TIMEOUT_SECONDS', '60'))
    )
    
    # API Configuration
    API_CONFIG = APIConfig(
        host=os.environ.get('API_HOST', '0.0.0.0'),
        port=int(os.environ.get('API_PORT', '8000')),
        debug=os.environ.get('API_DEBUG', 'False').lower() == 'true',
        reload=os.environ.get('API_RELOAD', 'True').lower() == 'true'
    )
    
    # UI Configuration
    UI_CONFIG = UIConfig(
        port=int(os.environ.get('UI_PORT', '8501')),
        address=os.environ.get('UI_ADDRESS', '0.0.0.0'),
        theme=os.environ.get('UI_THEME', 'light')
    )
    
    # Logging Configuration
    LOGGING_CONFIG = LoggingConfig(
        level=os.environ.get('LOG_LEVEL', 'INFO'),
        format=os.environ.get('LOG_FORMAT', '%(asctime)s | %(levelname)-8s - [%(relpathname)s %(funcName)s(%(lineno)d)] - %(message)s'),
        log_to_file=os.environ.get('LOG_TO_FILE', 'True').lower() == 'true',
        log_dir=os.environ.get('LOG_DIR', 'logs')
    )
    
    # Get default LLM based on environment variable
    @staticmethod
    def get_default_llm_config():
        default_llm = os.environ.get('DEFAULT_LLM', 'openai').lower()
        if default_llm == 'gemini':
            return Config.GEMINI_CONFIG
        elif default_llm == 'claude':
            return Config.CLAUDE_CONFIG
        else:
            return Config.OPENAI_CONFIG

