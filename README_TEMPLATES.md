# Agent Template System for Multi-Agent Framework

## Overview

The agent template system provides a structured way to create and customize agent profiles based on predefined templates. This enables the Dynamic Agent Proxy to efficiently generate specialized agents without having to create every configuration detail from scratch for each new query.

## Key Benefits

1. **Improved Efficiency**: The proxy can quickly create specialized agents by customizing predefined templates rather than generating configurations from scratch.

2. **Consistency**: Templates ensure a consistent approach to agent configurations while allowing customization.

3. **Caching**: Similar queries can reuse existing configurations, reducing latency.

4. **Tool Integration**: Templates include compatible tools that work well with each agent type.

5. **Specialization**: Templates can be customized for specific domains while maintaining their core expertise profile.

## Implementation Details

The implementation consists of several components:

### 1. Agent Templates (`src/agents/utils/agent_templates.py`)

Core classes:
- `AgentTemplate`: Represents a template for an agent profile that can be customized
- `AgentTemplateCache`: Caches recently used configurations for reuse
- `AgentTemplateManager`: Manages templates, tools, and template selection

### 2. Template and Tool Definitions

- `src/agents/templates/agent_templates.yaml`: Defines base templates for different agent types
- `src/agents/templates/tools_config.yaml`: Defines tools that can be used with different agent types

### 3. Dynamic Agent Proxy Integration

The `DynamicAgentProxy` class has been updated to:
- Use the template system to find appropriate templates for user queries
- Customize templates based on query analysis
- Cache and reuse configurations for similar queries
- Integrate tool-specific instructions into system messages

## Template Selection Process

1. When a user sends a query, the `DynamicAgentProxy._analyze_query()` method analyzes it using `QueryAnalyzer`
2. Based on the analysis, `find_best_template()` selects the most appropriate template
3. The template is customized with domain-specific details via `customize_template()`
4. Compatible tools are added to the configuration
5. The final configuration is used for processing the query
6. The configuration is cached for reuse with similar future queries

## Adding New Templates

Templates can be added by:
1. Adding a new entry to `agent_templates.yaml`
2. Defining the template structure, including base system message, expertise areas, etc.
3. Defining customization variables that can be used to specialize the template

## Adding New Tools

Tools can be added by:
1. Adding a new entry to `tools_config.yaml`
2. Specifying tool parameters, compatible templates, and system message additions
3. Setting any temperature adjustments needed when using the tool

## Testing

A test script is included to verify the template system functionality:
- `tests/test_agent_templates.py`: Tests template selection, customization, and caching
- `run_template_test.sh`: Shell script to run the tests

## Example Usage

```python
from src.agents.utils import get_template_manager, QueryAnalyzer

# Analyze a query
analyzer = QueryAnalyzer()
analysis = analyzer.analyze_query("How do I fix a memory leak in my Python code?")

# Get template manager
template_manager = get_template_manager()

# Find the best template for this query
template_id, variables = template_manager.find_best_template(analysis)

# Customize the template with query-specific variables
config = template_manager.customize_template(template_id, variables)

# Use the configuration with an LLM
# ...
```

This template system provides a flexible, efficient way to configure agents in the multi-agent framework, balancing standardization with customizability. 