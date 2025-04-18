# Multi-Agent System

A robust integration of the OpenAI Agents SDK enabling sophisticated multi-agent interactions and workflows.

## Features

- Seamless integration with OpenAI's Agents SDK
- Support for multiple agents with different roles and capabilities
- Configurable agent behaviors and interaction patterns
- Comprehensive logging and debugging capabilities
- Error handling and recovery mechanisms

## Prerequisites

- Python 3.9+
- OpenAI API key with appropriate permissions
- Bash-compatible shell (for the startup script)

## Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/multi-agent.git
   cd multi-agent
   ```

2. Create a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Set up your environment variables by creating a `.env` file:
   ```
   OPENAI_API_KEY=your_api_key_here
   OPENAI_ORG_ID=your_org_id  # Optional
   OPENAI_PROJECT_ID=your_project_id # Optional
   ```

## Usage

### Starting the Application

Use the startup script to launch the application:

```bash
# Make the startup script executable
chmod +x start.sh

# Start in normal mode
./start.sh

# Start in debug mode
./start.sh --debug
```

### Testing the SDK Integration

A test script is provided to verify the OpenAI Agents SDK integration:

```bash
# Make the test script executable
chmod +x test_openai_sdk.py

# Run basic test
./test_openai_sdk.py

# Run with debug logging
./test_openai_sdk.py --debug

# Test error handling
./test_openai_sdk.py --test-error
```

## Configuration

The system can be configured through:

1. Environment variables (set in `.env` file or directly in your shell)
2. Command-line arguments when starting the application
3. Configuration files (see `config/` directory)

### Key Environment Variables

- `OPENAI_API_KEY`: Your OpenAI API key (required)
- `OPENAI_DEBUG`: Set to "true" to enable debug mode
- `DEFAULT_LLM`: The default language model to use (e.g., "gpt-4-turbo-preview")

## Project Structure

```
multi-agent/
├── config/             # Configuration files
├── src/                # Source code
│   ├── app.py          # Main application entry point
│   ├── agents/         # Agent definitions and behaviors
│   ├── tools/          # Tool implementations
│   └── utils/          # Utility functions
├── test_openai_sdk.py  # SDK integration test
├── start.sh            # Startup script
├── requirements.txt    # Python dependencies
└── README.md           # This file
```

## Debugging

When running in debug mode:

1. Verbose logs will be generated
2. The OpenAI SDK's debug mode will be enabled
3. Additional diagnostic information will be displayed

Debug logs are stored in the `logs/` directory.

## Common Issues

### API Key Authentication Errors

If you encounter authentication errors, verify that:
- Your API key is correctly set in the `.env` file or as an environment variable
- Your API key has the necessary permissions
- Your account has access to the requested models

### Missing Dependencies

If you encounter import errors, ensure all dependencies are installed:
```bash
pip install -r requirements.txt
```

## License

This project is licensed under the MIT License - see the LICENSE file for details.
