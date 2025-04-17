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
    # Default values for environment variables
    # These serve as a second layer of fallbacks
    
    # Default LLM Selection
    DEFAULT_LLM = "openai"
    
    # Model type identifiers
    OPENAI_MODEL_TYPES = ["openai", "gpt", "azure"]  # Identifiers used to recognize OpenAI models
    GEMINI_MODEL_TYPES = ["gemini", "google"]        # Identifiers used to recognize Gemini models
    CLAUDE_MODEL_TYPES = ["claude", "anthropic"]     # Identifiers used to recognize Claude models
    
    # OpenAI Defaults
    OPENAI_API_KEY = ""
    OPENAI_MODEL_NAME = "GPT"
    OPENAI_MODEL_ID = "gpt-3.5-turbo"
    OPENAI_TEMPERATURE = 0.7
    OPENAI_MAX_TOKENS = 2048
    OPENAI_TOP_P = 1.0
    OPENAI_TOP_K = 40
    OPENAI_FREQUENCY_PENALTY = 0.0
    OPENAI_PRESENCE_PENALTY = 0.0
    OPENAI_API_BASE = ""
    OPENAI_ORGANIZATION_ID = ""
    OPENAI_API_VERSION = ""
    
    # Model lists for validation and special handling
    OPENAI_SMALL_MODELS = ["gpt-4.1-nano-2025-04-14", "gpt-4.1-nano", "gpt-4.1-mini-2025-04-14", "gpt-4.1-mini", "o3-mini-2025-01-31", "o3-mini"]
    
    # Gemini Defaults
    GOOGLE_API_KEY = ""
    GEMINI_MODEL_NAME = "Gemini"
    GEMINI_MODEL_ID = "models/gemini-1.5-flash"
    GEMINI_TEMPERATURE = 0.8
    GEMINI_MAX_TOKENS = 2048
    GEMINI_TOP_P = 0.8
    GEMINI_TOP_K = 40
    GEMINI_API_BASE = ""
    GEMINI_API_VERSION = ""
    
    # Claude Defaults
    ANTHROPIC_API_KEY = ""
    CLAUDE_MODEL_NAME = "Claude"
    CLAUDE_MODEL_ID = "claude-3-haiku-20240307"
    CLAUDE_TEMPERATURE = 0.7
    CLAUDE_MAX_TOKENS = 4000
    CLAUDE_TOP_P = 1.0
    ANTHROPIC_API_BASE = ""
    ANTHROPIC_API_VERSION = ""
    
    # Agent Configuration Defaults
    SAVE_CHAT = True
    VERBOSE_LOGGING = False
    MAX_RETRIES = 3
    TIMEOUT_SECONDS = 60
    
    # API Configuration Defaults
    API_HOST = "0.0.0.0"
    API_PORT = 8000
    API_DEBUG = False
    API_RELOAD = True
    
    # UI Configuration Defaults
    UI_PORT = 8501
    UI_ADDRESS = "0.0.0.0"
    UI_THEME = "light"
    
    # Logging Configuration Defaults
    LOG_LEVEL = "INFO"
    LOG_FORMAT = "%(asctime)s | %(levelname)-8s - [%(relpathname)s %(funcName)s(%(lineno)d)] - %(message)s"
    LOG_TO_FILE = True
    LOG_DIR = "logs"
    
    # LLM Configurations
    OPENAI_CONFIG = LLMConfig(
        api_key=os.environ.get('OPENAI_API_KEY', OPENAI_API_KEY),
        model_name=OPENAI_MODEL_NAME,
        model_id=os.environ.get('OPENAI_MODEL_ID', OPENAI_MODEL_ID),
        temperature=float(os.environ.get('OPENAI_TEMPERATURE', OPENAI_TEMPERATURE)),
        max_tokens=int(os.environ.get('OPENAI_MAX_TOKENS', OPENAI_MAX_TOKENS)),
        system_prompt=LLM_SYSTEM_PROMPT,
        top_p=float(os.environ.get('OPENAI_TOP_P', OPENAI_TOP_P)),
        top_k=int(os.environ.get('OPENAI_TOP_K', OPENAI_TOP_K)),
        frequency_penalty=float(os.environ.get('OPENAI_FREQUENCY_PENALTY', OPENAI_FREQUENCY_PENALTY)),
        presence_penalty=float(os.environ.get('OPENAI_PRESENCE_PENALTY', OPENAI_PRESENCE_PENALTY)),
        endpoint_config=LLMEndpointConfig(
            api_base=os.environ.get('OPENAI_API_BASE', OPENAI_API_BASE),
            organization_id=os.environ.get('OPENAI_ORGANIZATION_ID', OPENAI_ORGANIZATION_ID),
            api_version=os.environ.get('OPENAI_API_VERSION', OPENAI_API_VERSION)
        )
    )

    GEMINI_CONFIG = LLMConfig(
        api_key=os.environ.get('GOOGLE_API_KEY', GOOGLE_API_KEY),
        model_name=GEMINI_MODEL_NAME,
        model_id=os.environ.get('GEMINI_MODEL_ID', GEMINI_MODEL_ID),
        temperature=float(os.environ.get('GEMINI_TEMPERATURE', GEMINI_TEMPERATURE)),
        max_tokens=int(os.environ.get('GEMINI_MAX_TOKENS', GEMINI_MAX_TOKENS)),
        system_prompt=LLM_SYSTEM_PROMPT,
        top_p=float(os.environ.get('GEMINI_TOP_P', GEMINI_TOP_P)),
        top_k=int(os.environ.get('GEMINI_TOP_K', GEMINI_TOP_K)),
        endpoint_config=LLMEndpointConfig(
            api_base=os.environ.get('GEMINI_API_BASE', GEMINI_API_BASE),
            api_version=os.environ.get('GEMINI_API_VERSION', GEMINI_API_VERSION)
        )
    )
    
    CLAUDE_CONFIG = LLMConfig(
        api_key=os.environ.get('ANTHROPIC_API_KEY', ANTHROPIC_API_KEY),
        model_name=CLAUDE_MODEL_NAME,
        model_id=os.environ.get('CLAUDE_MODEL_ID', CLAUDE_MODEL_ID),
        temperature=float(os.environ.get('CLAUDE_TEMPERATURE', CLAUDE_TEMPERATURE)),
        max_tokens=int(os.environ.get('CLAUDE_MAX_TOKENS', CLAUDE_MAX_TOKENS)),
        system_prompt=LLM_SYSTEM_PROMPT,
        top_p=float(os.environ.get('CLAUDE_TOP_P', CLAUDE_TOP_P)),
        endpoint_config=LLMEndpointConfig(
            api_base=os.environ.get('ANTHROPIC_API_BASE', ANTHROPIC_API_BASE),
            api_version=os.environ.get('ANTHROPIC_API_VERSION', ANTHROPIC_API_VERSION)
        )
    )
    
    # Agent Configuration
    AGENT_CONFIG = AgentConfig(
        save_chat=os.environ.get('SAVE_CHAT', str(SAVE_CHAT)).lower() == 'true',
        verbose_logging=os.environ.get('VERBOSE_LOGGING', str(VERBOSE_LOGGING)).lower() == 'true',
        max_retries=int(os.environ.get('MAX_RETRIES', MAX_RETRIES)),
        timeout_seconds=int(os.environ.get('TIMEOUT_SECONDS', TIMEOUT_SECONDS))
    )
    
    # API Configuration
    API_CONFIG = APIConfig(
        host=os.environ.get('API_HOST', API_HOST),
        port=int(os.environ.get('API_PORT', API_PORT)),
        debug=os.environ.get('API_DEBUG', str(API_DEBUG)).lower() == 'true',
        reload=os.environ.get('API_RELOAD', str(API_RELOAD)).lower() == 'true'
    )
    
    # UI Configuration
    UI_CONFIG = UIConfig(
        port=int(os.environ.get('UI_PORT', UI_PORT)),
        address=os.environ.get('UI_ADDRESS', UI_ADDRESS),
        theme=os.environ.get('UI_THEME', UI_THEME)
    )
    
    # Logging Configuration
    LOGGING_CONFIG = LoggingConfig(
        level=os.environ.get('LOG_LEVEL', LOG_LEVEL),
        format=os.environ.get('LOG_FORMAT', LOG_FORMAT),
        log_to_file=os.environ.get('LOG_TO_FILE', str(LOG_TO_FILE)).lower() == 'true',
        log_dir=os.environ.get('LOG_DIR', LOG_DIR)
    )
    
    # Get default LLM based on environment variable
    @staticmethod
    def get_default_llm_config():
        default_llm = os.environ.get('DEFAULT_LLM', Config.DEFAULT_LLM).lower()
        if default_llm == 'gemini':
            return Config.GEMINI_CONFIG
        elif default_llm == 'claude':
            return Config.CLAUDE_CONFIG
        else:
            return Config.OPENAI_CONFIG

