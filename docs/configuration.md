# Configuration System

This document details the Multi-Agent system's centralized configuration architecture and how to customize it for your needs.

## Overview

The Multi-Agent system uses a modular, centralized configuration system that:

1. Loads settings from environment variables
2. Provides sensible defaults for all settings
3. Centralizes all prompts in one location
4. Makes it easy to customize LLM parameters
5. Supports different LLM providers (OpenAI, Google Gemini, Anthropic Claude)

## Core Components

### Configuration Files

The configuration system consists of these primary files:

- `src/config.py`: Main configuration module with settings classes
- `src/prompt.py`: Centralized repository for all system prompts
- `.env`: Your private configuration (not checked into version control)
- `.env.example`: Template showing all available configuration options

### Configuration Classes

The system uses Pydantic models for configuration, providing validation and type safety:

```python
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
```

Other configuration classes include:

- `AgentConfig`: Agent-specific settings
- `APIConfig`: FastAPI server configuration
- `UIConfig`: Streamlit UI configuration
- `LoggingConfig`: Logging settings

## Configuration Loading

The system uses a multi-layer fallback approach for configuration:

1. **Environment Variables**: First priority is given to settings in the `.env` file
2. **Class-level Defaults**: If environment variables aren't found, the system falls back to defaults defined in the `Config` class
3. **Pydantic Model Defaults**: As a final fallback, defaults defined in Pydantic models are used

This example demonstrates the fallback hierarchy:

```python
# Class-level default defined in Config class
OPENAI_MODEL_ID = "gpt-3.5-turbo"

# Configuration loading with fallbacks
OPENAI_CONFIG = LLMConfig(
    # First tries environment variable, then falls back to class default
    model_id=os.environ.get('OPENAI_MODEL_ID', OPENAI_MODEL_ID),
    # If both are missing, falls back to Pydantic model default
    temperature=float(os.environ.get('OPENAI_TEMPERATURE', OPENAI_TEMPERATURE)),
    # ... other settings
)
```

This multi-layer approach ensures that:
- The system always has sensible defaults even if no environment variables are set
- Critical values like API keys default to empty strings if not provided
- Settings are consistently available throughout the application

## Prompt Management

All system prompts are centralized in `src/prompt.py` using the same multi-layer fallback approach:

```python
class PromptDefaults:
    """Default values for all system prompts in the application."""
    
    # Default System Prompts
    LLM_SYSTEM_PROMPT = """
    You are a helpful AI assistant designed to provide clear, concise, and friendly responses...
    """
    # ... other prompt defaults

# Exported variables use environment variables with fallbacks to class defaults
LLM_SYSTEM_PROMPT = os.environ.get('LLM_SYSTEM_PROMPT', PromptDefaults.LLM_SYSTEM_PROMPT)
```

## Customizing the Configuration

### 1. Basic Configuration

For basic usage, simply modify the required API keys in your `.env` file:

```plaintext
OPENAI_API_KEY=your_openai_api_key
GOOGLE_API_KEY=your_google_api_key
ANTHROPIC_API_KEY=your_anthropic_api_key
```

### 2. Model Selection

You can choose which LLM provider to use by default:

```plaintext
DEFAULT_LLM=gemini  # Switch to using Gemini by default
```

And configure specific models for each provider:

```plaintext
OPENAI_MODEL_ID=gpt-4
GEMINI_MODEL_ID=models/gemini-pro
CLAUDE_MODEL_ID=claude-3-opus-20240229
```

### 3. Generation Parameters

Tune generation parameters for each model:

```plaintext
OPENAI_TEMPERATURE=0.8
OPENAI_MAX_TOKENS=4096
OPENAI_TOP_P=0.95
OPENAI_FREQUENCY_PENALTY=0.2
```

### 4. Custom Endpoints

For enterprise deployments or Azure OpenAI:

```plaintext
OPENAI_API_BASE=https://your-endpoint.openai.azure.com/
OPENAI_API_VERSION=2023-05-15
OPENAI_ORGANIZATION_ID=org-yourOrgId
```

### 5. Agent Behavior

Customize agent behavior:

```plaintext
SAVE_CHAT=True
VERBOSE_LOGGING=True
MAX_RETRIES=5
```

### 6. Custom Prompts

For advanced customization, override system prompts:

```plaintext
LLM_SYSTEM_PROMPT=You are a specialized AI assistant for our organization...
BASE_GENERATION_SYSTEM_PROMPT=Generate concise and accurate content following our style guide...
```

## Usage in Code

Configuration is used consistently throughout the codebase:

```python
# Import the configuration
from src.config import Config

# Initialize LLM with proper configuration
config = Config.OPENAI_CONFIG
model = OpenAI(
    api_key=config.api_key,
    model=config.model_id,
    temperature=config.temperature,
    max_tokens=config.max_tokens
)

# Access prompt templates
from src.prompt import PLANNING_INITIAL_PROMPT

prompt = PLANNING_INITIAL_PROMPT.format(
    task=user_query,
    tool_signatures=available_tools
)
```

## Common Configuration Patterns

### 1. Development Setup

For local development:

```plaintext
API_DEBUG=True
API_RELOAD=True
VERBOSE_LOGGING=True
LOG_LEVEL=DEBUG
```

### 2. Production Setup

For production deployment:

```plaintext
API_DEBUG=False
API_RELOAD=False
VERBOSE_LOGGING=False
LOG_LEVEL=INFO
API_HOST=0.0.0.0  # Accept connections from any IP
```

### 3. Testing Setup

For testing:

```plaintext
OPENAI_MODEL_ID=gpt-3.5-turbo  # Use cheaper model for testing
LOG_TO_FILE=False  # Avoid cluttering logs during tests
MAX_TOKENS=1024  # Smaller responses for faster tests
```

## Best Practices

1. **Never hardcode API keys** or sensitive information in the code
2. **Use environment-specific .env files** (.env.dev, .env.prod)
3. **Override only what you need** to change, rely on defaults otherwise
4. **Test configuration changes** before deploying to production
5. **Document custom prompts** when making significant changes

## Troubleshooting

### Common Issues

1. **LLM not working properly**:
   - Check that the API key is set correctly
   - Verify the model ID is valid for the provider
   - Ensure the API base URL is correct if using a custom endpoint

2. **Configuration not loading**:
   - Confirm .env file is in the correct location
   - Check for syntax errors in environment variables
   - Verify dotenv is loading properly

3. **Unexpected agent behavior**:
   - Review system prompt customizations
   - Check temperature and other generation parameters
   - Look at logs for any error messages

# Configuration Standard

This document outlines the configuration system used in the multi-agent application.

## Configuration Files

The application uses the following configuration-related files:

- `src/config.py`: Main configuration module with settings classes
- `src/settings.py`: Exports the global configuration instance

## Global Configuration Instance

The application uses a single global configuration instance to ensure consistency 
throughout the codebase. This instance is created in `src/settings.py` and can be 
imported using:

```python
from src.settings import global_settings
```

## Configuration Classes

All configuration settings are defined in `src/config.py` and grouped into relevant 
configuration classes.

### LLM Configuration

Configuration for specific Large Language Models:

```python
# Example: Using the global configuration instance
from src.settings import global_settings

# Access OpenAI configuration settings
openai_settings = global_settings.OPENAI_CONFIG

# Initialize model with settings
model = OpenAI(
    api_key=openai_settings.api_key,
    model=openai_settings.model_id,
    temperature=openai_settings.temperature,
    max_tokens=openai_settings.max_tokens
)
```

### Environment Variables

All configuration settings can be overridden by environment variables, which are 
loaded automatically by the Config class.

For example:
- `OPENAI_API_KEY` - Sets the API key for OpenAI
- `GOOGLE_API_KEY` - Sets the API key for Google/Gemini
- `ANTHROPIC_API_KEY` - Sets the API key for Anthropic/Claude

## Configuration Best Practices

1. Always import and use the global configuration instance:
   ```python
   from src.settings import global_settings
   ```

2. Do not create new Config() instances in your code. Instead, use the global instance.

3. For unit tests, you can create test-specific configuration instances, but in application
   code always use the global instance.

4. If adding new configuration settings, add them to the appropriate class in `src/config.py`. 