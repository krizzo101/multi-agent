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

Settings are loaded from environment variables with fallbacks to defaults:

```python
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
```

## Prompt Management

All system prompts are centralized in `src/prompt.py` and are also configurable via environment variables:

```python
# Classification Prompts
CLASSIFY_PROMPT = os.environ.get('CLASSIFY_PROMPT', """
You are AgentMatcher, an intelligent assistant designed to analyze user queries and match them with 
the most suitable agent or department. Your task is to understand the user request,
identify key entities and intents, and determine which agent or department would be best equipped
to handle the query.

# ... prompt content ...
""")
```

This makes it easy to modify agent behavior without changing code.

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