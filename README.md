# Multi-Agent
![picture](https://raw.githubusercontent.com/awslabs/multi-agent-orchestrator/main/img/flow.jpg)

## Introduction

This repository contains an implementation of agentic patterns such as **Planning (ReAct flow)**, **Reflection**, and **Multi-Agent** workflows. It showcases advanced agent orchestration with APIs and tools.

- Follow this repo to learn more about multi-agent patterns: [agentic_patterns](https://github.com/neural-maze/agentic_patterns/)
- Follow this repo to learn more about multi-agent orchestrator: [multi-agent-orchestrator](https://github.com/awslabs/multi-agent-orchestrator)

---

## Project Structure

```plaintext
multi-agent/
│
├── api/                     # API logic
│   ├── routers/             # API routers
│   └── services/            # Service logic
│       └── agent.py         # Main agent services
│
├── docker/                  # Docker setup
│   ├── Dockerfile.backend   # Backend Dockerfile
│   └── Dockerfile.frontend  # Frontend Dockerfile
│
├── src/                     # Source code
│   ├── agents/              # Agent-specific implementations
│   │   ├── llm/             # LLM implementations
│   │   ├── base.py          # Base agent classes
│   │   ├── manager_agent.py # Manager/orchestrator agent
│   │   ├── planning_agent.py # Planning agent (ReAct)
│   │   └── reflection_agent.py # Reflection agent
│   ├── prompt.py            # Centralized prompt definitions
│   ├── config.py            # Centralized configuration
│   └── tests/               # Test files
│       ├── agent_test.py    # Tests for agents
│       └── llm_test.py      # Tests for LLM functions
│
├── venv/                    # Virtual environment
├── app_fastapi.py           # FastAPI app
├── app_streamlit.py         # Streamlit app for UI
├── docker-compose.yaml      # Docker Compose setup
├── .env.example             # Environment variable template
├── requirements.txt         # Python dependencies
└── README.md                # Project documentation
```

---

## Installation

### 1. Clone the repository

```bash
git clone https://github.com/buithanhdam/multi-agent.git
cd multi-agent
```

### 2. Create and activate a virtual environment (Optional)

- **For Unix/macOS:**
  ```bash
  python3 -m venv venv
  source venv/bin/activate
  ```
- **For Windows:**
  ```bash
  python -m venv venv
  .\venv\Scripts\activate
  ```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

---

## Configuration

The system uses a centralized configuration approach where all settings are loaded from environment variables with sensible defaults.

### Environment Variables

Copy the `.env.example` file to a new `.env` file and update the necessary configuration:

```bash
cp .env.example .env
```

### Available Configuration Options

#### LLM API Keys

```plaintext
GOOGLE_API_KEY=your_google_api_key    # For Gemini models
OPENAI_API_KEY=your_openai_api_key    # For OpenAI models
ANTHROPIC_API_KEY=your_anthropic_api_key  # For Claude models
```

#### LLM Model Selection and Parameters

```plaintext
# Default LLM provider
DEFAULT_LLM=openai  # Options: openai, gemini, claude

# OpenAI Configuration
OPENAI_MODEL_ID=gpt-3.5-turbo
OPENAI_TEMPERATURE=0.7
OPENAI_MAX_TOKENS=2048
OPENAI_TOP_P=1.0
OPENAI_FREQUENCY_PENALTY=0.0
OPENAI_PRESENCE_PENALTY=0.0
OPENAI_API_BASE=  # Optional: for custom endpoints
OPENAI_ORGANIZATION_ID=  # Optional: for organization-specific usage

# Gemini Configuration
GEMINI_MODEL_ID=models/gemini-1.5-flash
GEMINI_TEMPERATURE=0.8
GEMINI_MAX_TOKENS=2048
GEMINI_TOP_P=0.8
GEMINI_TOP_K=40

# Claude Configuration
CLAUDE_MODEL_ID=claude-3-haiku-20240307
CLAUDE_TEMPERATURE=0.7
CLAUDE_MAX_TOKENS=4000
CLAUDE_TOP_P=1.0
```

#### System Prompts

You can customize the system prompts used by different agents:

```plaintext
LLM_SYSTEM_PROMPT=Your custom default system prompt
BASE_GENERATION_SYSTEM_PROMPT=Custom prompt for generation
BASE_REFLECTION_SYSTEM_PROMPT=Custom prompt for reflection
PLANNING_INITIAL_PROMPT=Custom prompt for planning
```

#### Agent Configuration

```plaintext
SAVE_CHAT=True  # Whether to save chat history
VERBOSE_LOGGING=False  # Enable verbose logging
MAX_RETRIES=3  # Maximum retries for failed operations
TIMEOUT_SECONDS=60  # Timeout for operations
```

#### API & UI Configuration

```plaintext
API_HOST=0.0.0.0
API_PORT=8000
API_DEBUG=False
API_RELOAD=True

UI_PORT=8501
UI_ADDRESS=0.0.0.0
UI_THEME=light
```

#### Logging Configuration

```plaintext
LOG_LEVEL=INFO
LOG_TO_FILE=True
LOG_DIR=logs
```

### Configuration Architecture

All configuration is centralized in the following files:

- `src/config.py`: Defines configuration classes and loads settings from environment variables
- `src/prompt.py`: Contains all system prompts used by the agents
- `.env`: Contains your private configuration values (not checked into version control)
- `.env.example`: Template showing all available configuration options

---

## Testing

- Run the test suite using `pytest`:

```bash
pytest src/tests/
```

- Or if you dont want to use `pytest` then run `python` cmd:

```bash
python3 src/tests/llm_test.py
```

```bash
python3 src/tests/agent_test.py
```

---

## Running the Application

### 1. Run FastAPI Backend

```bash
uvicorn app_fastapi:app --host 0.0.0.0 --port 8000 --reload
```

- Access the API at: `http://127.0.0.1:8000`

### 2. Run Streamlit Frontend

```bash
streamlit run app_streamlit.py --server.port=8501 --server.address=0.0.0.0
```

- Access the frontend UI at: `http://localhost:8501`

---

## Run with Docker

### 1. Build Docker Images
- If you dont have `docker-compose` use `docker compose` instead
```bash
docker-compose build
```

### 2. Start Docker Containers

```bash
docker-compose up
```

- The backend will be available at `http://localhost:8000`.
- The frontend will be available at `http://localhost:8501`.

### 3. Stop Docker Containers

To stop the running containers, press `Ctrl+C` or run:

```bash
docker-compose down
```

---

## Contributing

Feel free to open an issue or submit a pull request to improve this project.

---

## License

This project is licensed under the MIT License.

---

## References

- [Agentic Patterns Repo](https://github.com/neural-maze/agentic_patterns/)
- [Multi Agent Orchestrator](https://github.com/awslabs/multi-agent-orchestrator)
