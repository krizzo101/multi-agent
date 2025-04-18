"""
This module contains system prompts used by the different agents and LLMs in the application.
It provides both legacy direct access to prompts and integration with the template system.

For new code, use the template system via get_prompt() instead of accessing prompt constants directly.
"""

import os
import logging
from typing import Dict, Any, Optional

from src.templates import get_template_manager

logger = logging.getLogger(__name__)

class PromptDefaults:
    """Default values for all system prompts in the application.
    
    This class provides fallback values for prompt environment variables
    and centralizes all prompt defaults in one place.
    """
    
    # Default System Prompts
    LLM_SYSTEM_PROMPT = """
You are a helpful AI assistant designed to provide clear, concise, and friendly responses to a wide variety of queries. 
Be helpful, engaging, and provide information or assistance to the best of your abilities.
"""

    # Classification Prompts
    CLASSIFY_PROMPT = """
You are AgentMatcher, an intelligent assistant designed to analyze user queries and match them with 
the most suitable agent or department. Your task is to understand the user request,
identify key entities and intents, and determine which agent or department would be best equipped
to handle the query.

Important: The user input may be a follow-up response to a previous interaction.
The conversation history, including the name of the previously selected agent, is provided.
If the user's input appears to be a continuation of the previous conversation
(e.g., 'yes', 'ok', 'I want to know more', '1'), select the same agent as before.

Available agents and their capabilities: {agent_descriptions}

Based on the user input and chat history, determine the most appropriate agent and provide a confidence score (0-1).

Respond in JSON format:
{{
    "selected_agent": "agent_id",
    "confidence": 0.0,
    "reasoning": "brief explanation"
}}
        
User input: {user_input}
Recent chat history: {chat_history}
"""

    # Reflection Agent Prompts
    BASE_GENERATION_SYSTEM_PROMPT = """
Your task is to Generate the best content possible for the user's request.
If the user provides critique, respond with a revised version of your previous attempt.
You must always output the revised content.
"""

    BASE_REFLECTION_SYSTEM_PROMPT = """
You are tasked with generating critique and recommendations to the user's generated content.
If the user content has something wrong or something to be improved, output a list of recommendations and critiques.
If the user content is ok and there's nothing to change, output this: <OK>
Utilize available tools if necessary to improve or validate the content.
"""

    # Planning Agent Prompts
    PLANNING_INITIAL_PROMPT = """
You are a planning assistant with access to specific tools. Create a focused plan using ONLY the tools listed below.

Task to accomplish: {task}

Available tools and specifications:
{tool_signatures}

Important rules:
1. ONLY use the tools listed above - do not assume any other tools exist
2. If a tool doesn't exist for a specific need, use your general knowledge to provide information
3. For information retrieval tasks, immediately use the RAG search tool if available
4. Keep the plan simple and focused - avoid unnecessary steps
5. Never include web searches or external tool usage in the plan

Format your response as JSON:
{{
    "steps": [
        {{
            "description": "step description",
            "requires_tool": true/false,
            "tool_name": "tool_name or null",
            "is_required": true/false
        }},
        ...
    ]
}}
"""

    PLANNING_REFLECTION_PROMPT = """
Reflect on the current execution state and determine if the plan needs adjustment.
Only respond with a valid JSON object containing your analysis and decisions.

Current progress: {progress}
Last result: {last_result}
Remaining steps: {remaining_steps}

Available tools: {available_tools}

Respond with a JSON object in this exact format:
{{
    "decision": "continue",
    "reasoning": "brief explanation",
    "modifications": []
}}

OR if modifications are needed:
{{
    "decision": "modify",
    "reasoning": "brief explanation",
    "modifications": [
        {{
            "type": "add|modify|remove",
            "step_index": null,
            "new_description": "step description",
            "requires_tool": false,
            "tool_name": null
        }}
    ]
}}
Remove the ```json and ```
"""

# Legacy approach: direct environment variable overrides
# Default System Prompts
LLM_SYSTEM_PROMPT = os.environ.get('LLM_SYSTEM_PROMPT', PromptDefaults.LLM_SYSTEM_PROMPT)

# Classification Prompts
CLASSIFY_PROMPT = os.environ.get('CLASSIFY_PROMPT', PromptDefaults.CLASSIFY_PROMPT)

# Reflection Agent Prompts
BASE_GENERATION_SYSTEM_PROMPT = os.environ.get('BASE_GENERATION_SYSTEM_PROMPT', PromptDefaults.BASE_GENERATION_SYSTEM_PROMPT)
BASE_REFLECTION_SYSTEM_PROMPT = os.environ.get('BASE_REFLECTION_SYSTEM_PROMPT', PromptDefaults.BASE_REFLECTION_SYSTEM_PROMPT)

# Planning Agent Prompts
PLANNING_INITIAL_PROMPT = os.environ.get('PLANNING_INITIAL_PROMPT', PromptDefaults.PLANNING_INITIAL_PROMPT)
PLANNING_REFLECTION_PROMPT = os.environ.get('PLANNING_REFLECTION_PROMPT', PromptDefaults.PLANNING_REFLECTION_PROMPT)

# Legacy-to-template mappings
_LEGACY_TO_TEMPLATE_MAP = {
    'LLM_SYSTEM_PROMPT': 'system.llm_default',
    'CLASSIFY_PROMPT': 'agent.classify',
    'BASE_GENERATION_SYSTEM_PROMPT': 'agent.reflection.generation',
    'BASE_REFLECTION_SYSTEM_PROMPT': 'agent.reflection.critique',
    'PLANNING_INITIAL_PROMPT': 'agent.planning.initial',
    'PLANNING_REFLECTION_PROMPT': 'agent.planning.reflection',
}

# Template-to-legacy mappings (reverse of above)
_TEMPLATE_TO_LEGACY_MAP = {v: k for k, v in _LEGACY_TO_TEMPLATE_MAP.items()}

# This is populated the first time _create_initial_templates is called
_INITIAL_TEMPLATES_CREATED = False

def _create_initial_templates():
    """Create initial templates based on legacy prompt defaults.
    
    This ensures the template system is populated with defaults even if
    no template files exist yet.
    """
    global _INITIAL_TEMPLATES_CREATED
    
    if _INITIAL_TEMPLATES_CREATED:
        return
        
    template_manager = get_template_manager()
    
    # Force template dirs creation
    for dir_path in template_manager.template_dirs:
        os.makedirs(dir_path, exist_ok=True)
    
    # Check if we have existing templates
    template_manager.load_templates()
    if template_manager.templates:
        _INITIAL_TEMPLATES_CREATED = True
        return
    
    logger.info("Creating initial templates from legacy prompt defaults")
    
    # Create prompts directory structure
    prompts_dir = template_manager.template_dirs[0]
    os.makedirs(prompts_dir, exist_ok=True)
    
    # Create templates from legacy defaults
    template_files = {
        "system.yaml": {
            "llm_default": {
                "content": PromptDefaults.LLM_SYSTEM_PROMPT,
                "description": "Default system prompt for LLMs",
                "variables": []
            }
        },
        "agent.yaml": {
            "classify": {
                "content": PromptDefaults.CLASSIFY_PROMPT,
                "description": "Agent classification prompt",
                "variables": ["agent_descriptions", "user_input", "chat_history"]
            }
        },
        "agent_reflection.yaml": {
            "generation": {
                "content": PromptDefaults.BASE_GENERATION_SYSTEM_PROMPT,
                "description": "Reflection agent generation prompt",
                "variables": []
            },
            "critique": {
                "content": PromptDefaults.BASE_REFLECTION_SYSTEM_PROMPT,
                "description": "Reflection agent critique prompt",
                "variables": []
            }
        },
        "agent_planning.yaml": {
            "initial": {
                "content": PromptDefaults.PLANNING_INITIAL_PROMPT,
                "description": "Planning agent initial prompt",
                "variables": ["task", "tool_signatures"]
            },
            "reflection": {
                "content": PromptDefaults.PLANNING_REFLECTION_PROMPT,
                "description": "Planning agent reflection prompt",
                "variables": ["progress", "last_result", "remaining_steps", "available_tools"]
            }
        }
    }
    
    import yaml
    
    # Write template files
    for filename, templates in template_files.items():
        filepath = os.path.join(prompts_dir, filename)
        with open(filepath, 'w') as f:
            yaml.dump(templates, f, default_flow_style=False)
    
    # Reload templates
    template_manager.load_templates(force_reload=True)
    _INITIAL_TEMPLATES_CREATED = True
    
    logger.info(f"Created {len(template_manager.templates)} initial templates")


def get_prompt(prompt_id: str, variables: Dict[str, Any] = None) -> str:
    """Get a prompt from the template system.
    
    Args:
        prompt_id: ID of the prompt template to use
        variables: Variables to substitute in the template
    
    Returns:
        Rendered prompt
    """
    variables = variables or {}
    
    try:
        # Ensure initial templates are created if needed
        _create_initial_templates()
        
        # Get template manager
        template_manager = get_template_manager()
        
        # Try to get template from template system
        try:
            rendered = template_manager.render_template(prompt_id, variables)
            return rendered
        except ValueError:
            # Check if it's a legacy prompt ID that can be mapped
            if prompt_id in _LEGACY_TO_TEMPLATE_MAP:
                template_id = _LEGACY_TO_TEMPLATE_MAP[prompt_id]
                try:
                    rendered = template_manager.render_template(template_id, variables)
                    return rendered
                except ValueError:
                    # Fall through to next fallback
                    pass
            
            # Fall back to legacy direct access
            legacy_value = globals().get(prompt_id)
            if legacy_value and isinstance(legacy_value, str):
                try:
                    # Simple string substitution for legacy prompts
                    return legacy_value.format(**variables)
                except KeyError as e:
                    logger.error(f"Error formatting legacy prompt {prompt_id}: {str(e)}")
                    return legacy_value
            
            # Last resort: use default from PromptDefaults
            default_value = getattr(PromptDefaults, prompt_id, None)
            if default_value and isinstance(default_value, str):
                try:
                    return default_value.format(**variables)
                except KeyError as e:
                    logger.error(f"Error formatting default prompt {prompt_id}: {str(e)}")
                    return default_value
                
            # Nothing found
            logger.error(f"No prompt found for ID: {prompt_id}")
            return f"ERROR: Prompt '{prompt_id}' not found"
    except Exception as e:
        logger.error(f"Unexpected error in get_prompt for {prompt_id}: {str(e)}", exc_info=True)
        return f"ERROR: Failed to get prompt '{prompt_id}' due to: {str(e)}"


def get_prompt_for_scenario(context: Dict[str, Any], variables: Dict[str, Any] = None) -> Optional[str]:
    """Get a prompt template based on scenario detection.
    
    Args:
        context: Context information for scenario detection
        variables: Variables to substitute in the template
    
    Returns:
        Rendered prompt or None if no suitable template found
    """
    # Ensure initial templates are created
    _create_initial_templates()
    
    template_manager = get_template_manager()
    return template_manager.render_for_scenario(context, variables)