from dataclasses import dataclass
from pydantic import BaseModel, Field, ValidationError
import dotenv 
dotenv.load_dotenv()
import os
from src.prompt import (LLM_SYSTEM_PROMPT)
from typing import Any, Dict

# --- YAML Support ---
try:
    from ruamel.yaml import YAML
    _yaml_loader = YAML(typ="safe")
    def load_yaml(path):
        with open(path, 'r') as f:
            return _yaml_loader.load(f)
except ImportError:
    import yaml
    def load_yaml(path):
        with open(path, 'r') as f:
            return yaml.safe_load(f)

# --- CONFIGURATION LOADER ---
def _deep_update(d: dict, u: dict) -> dict:
    for k, v in u.items():
        if isinstance(v, dict) and isinstance(d.get(k), dict):
            d[k] = _deep_update(d.get(k, {}), v)
        else:
            d[k] = v
    return d

def _env_override(config: dict, prefix: str = "") -> dict:
    for k, v in config.items():
        env_key = (prefix + k).upper()
        if isinstance(v, dict):
            config[k] = _env_override(v, env_key + "_")
        else:
            env_val = os.environ.get(env_key)
            if env_val is not None:
                # Try to cast to the type of v
                try:
                    if isinstance(v, bool):
                        config[k] = env_val.lower() in ("1", "true", "yes")
                    elif isinstance(v, int):
                        config[k] = int(env_val)
                    elif isinstance(v, float):
                        config[k] = float(env_val)
                    else:
                        config[k] = env_val
                except Exception:
                    config[k] = env_val
    return config

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
    api_key: str = ""
    model_name: str = "o3-mini"
    model_id: str = "o3-mini"
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
    """Configuration for logging"""
    level: str = "INFO"
    format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    file_path: str = "global.log"
    file_enabled: bool = True
    console_enabled: bool = True
    
    def setup_logging(self):
        """Configure the logging system based on current settings"""
        import logging
        
        # Create formatter
        formatter = logging.Formatter(self.format)
        
        # Convert level string to actual level
        level = getattr(logging, self.level.upper(), logging.INFO)
        
        # Configure root logger
        root_logger = logging.getLogger()
        root_logger.setLevel(level)
        
        # Remove any existing handlers to avoid duplicates
        for handler in root_logger.handlers[:]:
            root_logger.removeHandler(handler)
        
        # Add console handler if enabled
        if self.console_enabled:
            console = logging.StreamHandler()
            console.setLevel(level)
            console.setFormatter(formatter)
            root_logger.addHandler(console)
        
        # Add file handler if enabled
        if self.file_enabled and self.file_path:
            try:
                file_handler = logging.FileHandler(self.file_path, mode='a')
                file_handler.setLevel(level)
                file_handler.setFormatter(formatter)
                root_logger.addHandler(file_handler)
                
                # Log a startup message to verify logging is working
                root_logger.info("Logging system initialized")
            except Exception as e:
                # Log to console if file logging fails
                root_logger.error(f"Failed to setup file logging: {str(e)}")
        
        return root_logger

# --- YAML + ENV CONFIG LOADING ---
def load_config_yaml_env(yaml_path: str = "config.yaml") -> Dict[str, Any]:
    config = {}
    if os.path.exists(yaml_path):
        config = load_yaml(yaml_path) or {}
    config = _env_override(config)
    return config

# --- MAIN CONFIG CLASS (ENHANCED) ---
class Config:
    """
    Enhanced configuration loader supporting YAML, env vars, schema validation, and legacy compatibility.
    Usage:
        from src.config import Config
        config = Config()
        llm_config = config.llm
        api_config = config.api
    """
    # Default LLM type
    DEFAULT_LLM = "openai"
    
    def __init__(self, yaml_path: str = "config.yaml"):
        # Load YAML and env
        raw = load_config_yaml_env(yaml_path)
        
        # Initialize with default values and override with loaded config
        self.llm = LLMConfig(**raw.get("llm", {}))
        self.agent = AgentConfig(**raw.get("agent", {}))
        self.api = APIConfig(**raw.get("api", {}))
        self.ui = UIConfig(**raw.get("ui", {}))
        self.logging = LoggingConfig(**raw.get("logging", {}))
        
        # Initialize provider-specific configs
        gemini_defaults = {
            "api_key": os.environ.get("GOOGLE_API_KEY", ""),
            "model_name": "Gemini",
            "model_id": "models/gemini-1.5-flash",
            "temperature": 0.8,
            "max_tokens": 2048,
            "system_prompt": LLM_SYSTEM_PROMPT,
            "top_p": 0.8,
            "top_k": 40,
            "endpoint_config": {
                "api_base": "",
                "api_version": ""
            }
        }
        
        claude_defaults = {
            "api_key": os.environ.get("ANTHROPIC_API_KEY", ""),
            "model_name": "Claude",
            "model_id": "claude-3.7-sonnet-thinking",
            "temperature": 0.7,
            "max_tokens": 4000,
            "system_prompt": LLM_SYSTEM_PROMPT,
            "top_p": 1.0,
            "endpoint_config": {
                "api_base": "",
                "api_version": ""
            }
        }
        
        # Store provider-specific configs
        self.OPENAI_CONFIG = self.llm
        self.GEMINI_CONFIG = LLMConfig(**gemini_defaults)
        self.CLAUDE_CONFIG = LLMConfig(**claude_defaults)
        
        try:
            # Validate all configurations
            self.llm = LLMConfig(**raw.get("llm", {}))
            self.agent = AgentConfig(**raw.get("agent", {}))
            self.api = APIConfig(**raw.get("api", {}))
            self.ui = UIConfig(**raw.get("ui", {}))
            self.logging = LoggingConfig(**raw.get("logging", {}))
        except ValidationError as e:
            raise RuntimeError(f"Configuration validation error: {e}")

    @staticmethod
    def get_default_llm_config():
        """Get default LLM configuration based on environment variable"""
        config = Config()
        default_llm = os.environ.get('DEFAULT_LLM', Config.DEFAULT_LLM).lower()
        if default_llm == 'gemini':
            return config.GEMINI_CONFIG
        elif default_llm == 'claude':
            return config.CLAUDE_CONFIG
        else:
            return config.OPENAI_CONFIG

# --- LEGACY ADAPTER ---
class LegacyAdapter:
    """
    Provides backward compatibility for legacy config API.
    Usage:
        from src.config import LegacyAdapter
        legacy = LegacyAdapter()
        openai_key = legacy.OPENAI_API_KEY
    """
    def __init__(self, config: Config = None):
        self._config = config or Config()
        # OpenAI configurations
        self.OPENAI_API_KEY = self._config.llm.api_key
        self.OPENAI_MODEL_NAME = self._config.llm.model_name
        self.OPENAI_MODEL_ID = self._config.llm.model_id
        self.OPENAI_TEMP = self._config.llm.temperature
        self.OPENAI_MAX_TOKENS = self._config.llm.max_tokens
        self.OPENAI_TOP_P = self._config.llm.top_p
        self.OPENAI_TOP_K = self._config.llm.top_k
        self.OPENAI_FREQUENCY_PENALTY = self._config.llm.frequency_penalty
        self.OPENAI_PRESENCE_PENALTY = self._config.llm.presence_penalty
        self.OPENAI_API_BASE = self._config.llm.endpoint_config.api_base
        self.OPENAI_ORG_ID = self._config.llm.endpoint_config.organization_id
        self.OPENAI_API_VERSION = self._config.llm.endpoint_config.api_version
        
        # Gemini configurations
        self.GOOGLE_API_KEY = self._config.GEMINI_CONFIG.api_key
        self.GEMINI_MODEL_NAME = self._config.GEMINI_CONFIG.model_name
        self.GEMINI_MODEL_ID = self._config.GEMINI_CONFIG.model_id
        self.GEMINI_TEMPERATURE = self._config.GEMINI_CONFIG.temperature
        self.GEMINI_MAX_TOKENS = self._config.GEMINI_CONFIG.max_tokens
        self.GEMINI_TOP_P = self._config.GEMINI_CONFIG.top_p
        self.GEMINI_TOP_K = self._config.GEMINI_CONFIG.top_k
        self.GEMINI_API_BASE = self._config.GEMINI_CONFIG.endpoint_config.api_base
        self.GEMINI_API_VERSION = self._config.GEMINI_CONFIG.endpoint_config.api_version
        
        # Claude configurations
        self.ANTHROPIC_API_KEY = self._config.CLAUDE_CONFIG.api_key
        self.CLAUDE_MODEL_NAME = self._config.CLAUDE_CONFIG.model_name
        self.CLAUDE_MODEL_ID = self._config.CLAUDE_CONFIG.model_id
        self.CLAUDE_TEMPERATURE = self._config.CLAUDE_CONFIG.temperature
        self.CLAUDE_MAX_TOKENS = self._config.CLAUDE_CONFIG.max_tokens
        self.CLAUDE_TOP_P = self._config.CLAUDE_CONFIG.top_p
        self.ANTHROPIC_API_BASE = self._config.CLAUDE_CONFIG.endpoint_config.api_base
        self.ANTHROPIC_API_VERSION = self._config.CLAUDE_CONFIG.endpoint_config.api_version
        
        # Agent configurations
        self.SAVE_CHAT = self._config.agent.save_chat
        self.VERBOSE_LOGGING = self._config.agent.verbose_logging
        self.MAX_RETRIES = self._config.agent.max_retries
        self.TIMEOUT_SECONDS = self._config.agent.timeout_seconds
        
        # API configurations
        self.API_HOST = self._config.api.host
        self.API_PORT = self._config.api.port
        self.API_DEBUG = self._config.api.debug
        self.API_RELOAD = self._config.api.reload
        
        # UI configurations
        self.UI_PORT = self._config.ui.port
        self.UI_ADDRESS = self._config.ui.address
        self.UI_THEME = self._config.ui.theme
        
        # Logging configurations
        self.LOG_LEVEL = self._config.logging.level
        self.LOG_FORMAT = self._config.logging.format
        self.LOG_TO_FILE = self._config.logging.file_enabled
        self.LOG_DIR = self._config.logging.file_path

# Model type identifiers
OPENAI_MODEL_TYPES = ["openai", "gpt", "azure", "o3"]  # Identifiers used to recognize OpenAI models
GEMINI_MODEL_TYPES = ["gemini", "google"]        # Identifiers used to recognize Gemini models
CLAUDE_MODEL_TYPES = ["claude", "anthropic"]     # Identifiers used to recognize Claude models
OPENAI_SMALL_MODELS = ["gpt-4.1-nano", "gpt-4.1-mini", "o3-mini", "gpt-4o-mini"]

# Create default configuration instances
config = Config()
legacy = LegacyAdapter(config)

# Make model type identifiers accessible via the global config instance
config.OPENAI_MODEL_TYPES = OPENAI_MODEL_TYPES
config.GEMINI_MODEL_TYPES = GEMINI_MODEL_TYPES
config.CLAUDE_MODEL_TYPES = CLAUDE_MODEL_TYPES
config.OPENAI_SMALL_MODELS = OPENAI_SMALL_MODELS

# Create configuration instances for easy access
AGENT_CONFIG = config.agent
API_CONFIG = config.api
UI_CONFIG = config.ui
LOGGING_CONFIG = config.logging

# All legacy global configuration variables and functions have been removed.
# Configuration is now exclusively handled by the Config class and LegacyAdapter.

