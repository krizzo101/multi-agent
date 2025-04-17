"""
Template manager for the Multi-Agent Framework.

This module provides a flexible template system for managing and rendering
prompt templates used by agents.
"""

import os
import yaml
import logging
import glob
from typing import Dict, Any, List, Optional, Union
import chevron  # For Mustache template rendering
from pathlib import Path

logger = logging.getLogger(__name__)

class TemplateCache:
    """Cache for templates to avoid reloading from disk frequently."""
    
    def __init__(self):
        self.templates: Dict[str, Dict[str, Any]] = {}
        self.partials: Dict[str, str] = {}
        self.last_load_time: float = 0
    
    def clear(self):
        """Clear the cache."""
        self.templates = {}
        self.partials = {}
        self.last_load_time = 0

# Global cache instance
_template_cache = TemplateCache()

# Global template manager instance
_template_manager = None


class TemplateManager:
    """Manager for prompt templates using Mustache syntax."""
    
    def __init__(self, template_dirs: List[str] = None):
        """Initialize the template manager.
        
        Args:
            template_dirs: List of directories to search for templates, in priority order
        """
        self.template_dirs = template_dirs or []
        
        # Set default template directories if none provided
        if not self.template_dirs:
            base_dir = Path(__file__).parent.absolute()
            self.template_dirs = [
                os.path.join(base_dir, "prompts"),
                os.path.join(base_dir, "partials")
            ]
        
        # Ensure all template dirs exist
        for dir_path in self.template_dirs:
            os.makedirs(dir_path, exist_ok=True)
        
        # Initialize cache reference
        self.cache = _template_cache
        
        # Scenario mapper (populated during load)
        self.scenario_mappers = {}
    
    @property
    def templates(self) -> Dict[str, Dict[str, Any]]:
        """Get all templates from the cache."""
        return self.cache.templates
    
    @property
    def partials(self) -> Dict[str, str]:
        """Get all partials from the cache."""
        return self.cache.partials
    
    def load_templates(self, force_reload: bool = False) -> None:
        """Load all templates from disk.
        
        Args:
            force_reload: Force reload even if already loaded
        """
        if self.cache.templates and not force_reload:
            return
        
        self.cache.clear()
        
        # Load prompt templates (*.yaml files in prompts directory)
        for template_dir in self.template_dirs:
            prompt_pattern = os.path.join(template_dir, "*.yaml")
            partial_pattern = os.path.join(template_dir, "*.yaml")
            
            # Load prompt templates
            for yaml_file in glob.glob(prompt_pattern):
                try:
                    with open(yaml_file, 'r') as f:
                        templates = yaml.safe_load(f) or {}
                    
                    # Skip non-dictionary files
                    if not isinstance(templates, dict):
                        continue
                    
                    # Add templates to cache
                    for template_id, template_data in templates.items():
                        if isinstance(template_data, dict) and "content" in template_data:
                            if template_id in self.cache.templates:
                                logger.warning(f"Template {template_id} already exists, overwriting")
                            self.cache.templates[template_id] = template_data
                        else:
                            # Handle flat key-value structure (for partials)
                            self.cache.partials[template_id] = template_data
                except Exception as e:
                    logger.error(f"Error loading templates from {yaml_file}: {str(e)}")
        
        # Load scenario mappers if present (scenario_*.yaml files)
        for template_dir in self.template_dirs:
            scenario_pattern = os.path.join(template_dir, "scenario_*.yaml")
            
            for yaml_file in glob.glob(scenario_pattern):
                try:
                    with open(yaml_file, 'r') as f:
                        scenario_data = yaml.safe_load(f) or {}
                    
                    if not isinstance(scenario_data, dict):
                        continue
                    
                    # Extract mapper name from filename (scenario_NAME.yaml -> NAME)
                    mapper_name = os.path.basename(yaml_file).replace("scenario_", "").replace(".yaml", "")
                    self.scenario_mappers[mapper_name] = scenario_data
                except Exception as e:
                    logger.error(f"Error loading scenario mapper from {yaml_file}: {str(e)}")
        
        logger.info(f"Loaded {len(self.cache.templates)} templates, {len(self.cache.partials)} partials, and {len(self.scenario_mappers)} scenario mappers")
        
    def render_template(self, template_id: str, variables: Dict[str, Any] = None) -> str:
        """Render a template with variables.
        
        Args:
            template_id: ID of the template to render
            variables: Variables to substitute in the template
        
        Returns:
            Rendered template
        
        Raises:
            ValueError: If template not found
        """
        variables = variables or {}
        
        # Ensure templates are loaded
        if not self.cache.templates:
            self.load_templates()
        
        # Find template
        template_data = self.cache.templates.get(template_id)
        if not template_data:
            logger.error(f"Template not found: {template_id}")
            raise ValueError(f"Template not found: {template_id}")
        
        # Get template content
        template_content = template_data.get("content", "")
        if not template_content:
            logger.warning(f"Template {template_id} has no content")
            return ""
        
        # Render template with variables
        try:
            # Check if chevron is available, otherwise fallback to string format
            try:
                import chevron
                return chevron.render(
                    template=template_content,
                    data=variables,
                    partials_dict=self.cache.partials
                ).strip()
            except (ImportError, AttributeError):
                # Fallback to basic string format
                return template_content.format(**variables).strip()
        except Exception as e:
            logger.error(f"Error rendering template {template_id}: {str(e)}")
            return template_content  # Return unrendered as fallback
    
    def render_for_scenario(self, context: Dict[str, Any], variables: Dict[str, Any] = None) -> Optional[str]:
        """Render a template based on scenario matching.
        
        Args:
            context: Context information for scenario matching
            variables: Variables to substitute in the template
        
        Returns:
            Rendered template or None if no suitable template found
        """
        variables = variables or {}
        
        # Ensure templates are loaded
        if not self.cache.templates:
            self.load_templates()
        
        # Get scenario components from context
        components = {
            "agent_type": context.get("agent_type", ""),
            "conversation_stage": context.get("conversation_stage", ""),
            "intent": context.get("intent", ""),
        }
        
        # Find matching scenario in mappers
        matched_template_id = None
        
        for mapper_name, scenarios in self.scenario_mappers.items():
            for scenario_id, scenario_data in scenarios.items():
                if not isinstance(scenario_data, dict):
                    continue
                
                # Check if scenario components match context
                conditions = scenario_data.get("conditions", {})
                if not conditions:
                    continue
                
                is_match = True
                for key, expected in conditions.items():
                    if key not in components:
                        is_match = False
                        break
                    
                    actual = components[key]
                    if isinstance(expected, list):
                        if actual not in expected:
                            is_match = False
                            break
                    elif actual != expected:
                        is_match = False
                        break
                
                if is_match:
                    matched_template_id = scenario_data.get("template_id")
                    logger.debug(f"Matched scenario {scenario_id} to template {matched_template_id}")
                    break
            
            if matched_template_id:
                break
        
        # Render matched template
        if matched_template_id:
            try:
                return self.render_template(matched_template_id, variables)
            except ValueError:
                logger.warning(f"Template {matched_template_id} not found for scenario")
        
        # Fallback to direct template
        if "agent_type" in context and "conversation_stage" in context:
            direct_template_id = f"{context['agent_type']}.{context['conversation_stage']}"
            try:
                return self.render_template(direct_template_id, variables)
            except ValueError:
                logger.debug(f"No direct template found for {direct_template_id}")
        
        # No template found
        return None
    
    def get_prompt_for_context(self, context: Dict[str, Any]) -> Optional[str]:
        """Legacy method name for render_for_scenario."""
        return self.render_for_scenario(context)


def get_template_manager() -> TemplateManager:
    """Get the global template manager instance."""
    global _template_manager
    
    if _template_manager is None:
        _template_manager = TemplateManager()
    
    return _template_manager 