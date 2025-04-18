# Agent Template System

This directory contains the template system for agent profiles in the multi-agent framework. The template system allows the dynamic proxy to quickly configure specialized agents based on predefined templates, rather than generating every detail from scratch each time.

## Overview

The template system provides:

1. **Predefined Agent Profiles**: Basic configurations for different types of agents (developer, data scientist, researcher, etc.)
2. **Tool Configurations**: Definitions of tools that can be used by different agent types
3. **Template Customization**: Ability to specialize templates for specific domains and tasks
4. **Caching**: Remembering recently used configurations for similar queries

## Files

- `agent_templates.yaml`: Defines the base templates for different agent types
- `tools_config.yaml`: Defines tools that can be used by different agent templates

## Agent Templates

Each agent template includes:

- **Base system message**: The foundation for the agent's instructions
- **Expertise areas**: Domains the agent specializes in
- **Temperature range**: Valid temperature settings for this agent type
- **Supported tools**: Tools that work well with this agent type
- **Template variables**: Customization points in the template

Templates can be customized with variables such as:

- `specialization`: The specific domain specialization (e.g., "Python" for a Developer)
- `additional_instructions`: Extra guidelines for the agent
- `expertise_domains`: Additional areas of expertise
- `tools`: Specific tools to enable for this agent

## Tools Configuration

Tool configurations include:

- **Description**: What the tool does
- **Parameters**: Required inputs for the tool
- **Compatible with**: Which agent templates can use this tool
- **Temperature adjustment**: How the tool affects the agent's temperature setting
- **System prompt addition**: Text to add to the system message when the tool is enabled

## How It Works

1. When a user sends a query, the `DynamicAgentProxy` analyzes it using `QueryAnalyzer`
2. The system then finds the best matching template for the query
3. The template is customized with the specific domain, expertise areas, etc.
4. Tool configurations are added based on the template and query needs
5. The final configuration is used to process the query
6. The configuration is cached for similar future queries

## Extending the System

### Adding New Agent Templates

To add a new agent template, edit `agent_templates.yaml` and add a new entry:

```yaml
new_template_id:
  name: "Template Name"
  description: "Template description"
  base_system_message: |
    You are a specialized {specialization} Agent...
    
    {additional_instructions}
  expertise_areas:
    - area1
    - area2
  temperature_range: [0.1, 0.7]
  supported_tools:
    - tool1
    - tool2
  template_variables:
    - specialization
    - additional_instructions
```

### Adding New Tools

To add a new tool, edit `tools_config.yaml` and add a new entry:

```yaml
new_tool_id:
  description: "What the tool does"
  parameters:
    - param1
    - param2
  compatible_with:
    - template_id1
    - template_id2
  temperature_adjustment: -0.1
  system_prompt_addition: |
    You have access to a tool that can...
```

## Programmatic Usage

The template system can be accessed from code using:

```python
from src.agents.utils import get_template_manager

# Get the template manager
template_manager = get_template_manager()

# Get a template
template = template_manager.get_template("developer")

# Customize a template
config = template_manager.customize_template(
    "developer",
    {
        "specialization": "Python",
        "additional_instructions": "Focus on best practices for security."
    }
)

# Find best template for a query analysis
template_id, variables = template_manager.find_best_template(analysis)
``` 