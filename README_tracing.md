# OpenAI Agents SDK Tracing Guide

This guide explains how to use the OpenAI Agents SDK tracing functionality with the Multi-Agent Framework.

## Overview

The OpenAI Agents SDK includes powerful tracing capabilities that allow you to:

- Visualize agent interactions and decision-making processes
- Debug complex agent behaviors
- Monitor performance and resource usage
- Understand how agents are using tools and responding to user queries

## Quick Start

To start the application with tracing enabled, use the `start_with_openai_tracing.sh` script:

```bash
./start_with_openai_tracing.sh
```

This will launch the application with basic tracing enabled and store traces in a timestamped directory under the `traces/` folder.

## Implementation Details

The tracing system is implemented through several components working together:

1. **start_with_openai_tracing.sh**: Sets up environment variables and creates timestamped directories
2. **start_app.sh**: Detects tracing configuration and passes environment variables to the application
3. **src/agents/llm/openai_agents_sdk.py**: Configures the SDK's tracing system based on environment variables

The `_setup_tracing()` method in the OpenAI Agents SDK implementation checks for these environment variables:
- `OPENAI_TRACE_LEVEL`: Controls the tracing detail level
- `OPENAI_TRACE_DIR`: Specifies where traces are stored
- `OPENAI_AGENTS_TRACE_EXPORT`: Enables export to OpenAI's tracing service

When enabled, the system automatically configures appropriate trace processors based on the selected trace level.

## Tracing Options

The script supports several command-line options:

```bash
./start_with_openai_tracing.sh --trace-level=detailed --debug
```

Available options:

- `--debug`: Enable debug mode with verbose logging
- `--trace-level=LEVEL`: Set the tracing level (options below)
- `--help`: Show usage information

### Trace Levels

The script supports three tracing levels:

1. **basic** (default): Captures essential trace information with minimal performance impact
2. **detailed**: Captures more comprehensive trace data including tool calls and responses
3. **full**: Enables all tracing features including visualization capabilities

## Trace Directory Structure

Traces are stored in timestamped directories under the `traces/` folder:

```
traces/
  ├── 20230701_120000/  # Session from July 1, 2023 at 12:00:00
  │   ├── trace_123abc.json
  │   ├── trace_456def.json
  │   └── ...
  └── 20230702_150000/  # Session from July 2, 2023 at 15:00:00
      ├── trace_789ghi.json
      └── ...
```

## Viewing Traces

After running a session with tracing enabled, the script will display a summary of the traces collected. 

To visualize traces (requires the OpenAI Agents SDK visualization package):

```bash
python -m agents.viz.trace_viewer traces/20230701_120000
```

You may need to install the visualization package first:

```bash
pip install "openai-agents[viz]"
```

## How Tracing Works

The OpenAI Agents SDK uses a sophisticated tracing system that captures:

1. **Spans**: Individual operations like function calls or model generations
2. **Traces**: Collections of spans that represent a complete user interaction
3. **Metadata**: Additional information about each span or trace

Traces are processed by the `BatchTraceProcessor` which batches and exports them to an OpenAI endpoint when using the "full" trace level, or stores them locally otherwise.

## Troubleshooting

If you encounter issues with tracing:

1. Ensure your OpenAI API key has the necessary permissions
2. Check that the `traces/` directory is writable
3. Try increasing the trace level for more detailed information
4. Look for error messages in the application logs

## Environment Variables

The script sets several environment variables that control tracing behavior:

- `OPENAI_TRACE_LEVEL`: Sets the level of detail in traces
- `OPENAI_BETA`: Enables beta features for tracing
- `OPENAI_TRACE_DIR`: Directory where traces are stored
- `OPENAI_AGENTS_TRACE_EXPORT`: Controls whether traces are exported to OpenAI

You can also set these variables manually in your `.env` file if needed.

## Advanced Usage

For advanced use cases, you can modify the script or set additional environment variables:

- Configure custom trace processors
- Adjust batch sizes and export intervals
- Implement custom span exporters
- Add application-specific trace data

## Performance Considerations

Higher trace levels may impact application performance. If you experience slowdowns:

1. Use the "basic" trace level for production environments
2. Limit tracing to specific debug sessions
3. Consider increasing the batch size to reduce export frequency 