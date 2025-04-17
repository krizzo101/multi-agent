"""
Template Manager for the Prompt Template System.

This module provides the core infrastructure for loading, caching, and
providing prompt templates to agents. It supports variable substitution,
template assembly, and scenario-based template selection.
"""

import os
import yaml
import json
import logging
import re
from typing import Dict, Any, List, Optional, Set, Tuple
from pathlib import Path
import time
import hashlib
from functools import lru_cache

logger = logging.getLogger(__name__)

# Default template directories
DEFAULT_TEMPLATE_DIRS = [
    os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "templates", "prompts"),
    os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "templates", "components"),
]

# Cache settings
DEFAULT_CACHE_SIZE = 100
DEFAULT_CACHE_TTL = 300  # 5 minutes


class TemplateCache:
    """A cache for storing rendered templates to avoid repeated processing."""
    
    def __init__(self, max_size: int = DEFAULT_CACHE_SIZE, ttl: int = DEFAULT_CACHE_TTL):
        """Initialize the template cache.
        
        Args:
            max_size: Maximum number of templates to store in the cache
            ttl: Time-to-live for cache entries in seconds
        """
        self.max_size = max_size
        self.ttl = ttl
        self.cache: Dict[str, Tuple[str, float]] = {}
        
    def get(self, key: str) -> Optional[str]:
        """Get a template from the cache if it exists and is not expired.
        
        Args:
            key: The cache key
            
        Returns:
            The cached template or None if not found or expired
        """
        if key not in self.cache:
            return None
            
        template, timestamp = self.cache[key]
        
        # Check if the entry has expired
        if time.time() - timestamp > self.ttl:
            # Remove expired entry
            del self.cache[key]
            return None
            
        return template
        
    def set(self, key: str, template: str) -> None:
        """Add a template to the cache.
        
        Args:
            key: The cache key
            template: The rendered template
        """
        # If cache is full, remove the oldest entry
        if len(self.cache) >= self.max_size:
            oldest_key = min(self.cache.keys(), key=lambda k: self.cache[k][1])
            del self.cache[oldest_key]
            
        self.cache[key] = (template, time.time())
        
    def clear(self) -> None:
        """Clear the entire cache."""
        self.cache.clear()
        
    def invalidate(self, pattern: str) -> int:
        """Invalidate cache entries matching a pattern.
        
        Args:
            pattern: Regex pattern to match against keys
            
        Returns:
            Number of invalidated entries
        """
        regex = re.compile(pattern)
        keys_to_remove = [k for k in self.cache.keys() if regex.search(k)]
        
        for key in keys_to_remove:
            del self.cache[key]
            
        return len(keys_to_remove)


class TemplateManager:
    """Manager for loading, processing, and caching prompt templates."""
    
    def __init__(
        self,
        template_dirs: List[str] = None,
        cache_size: int = DEFAULT_CACHE_SIZE,
        cache_ttl: int = DEFAULT_CACHE_TTL
    ):
        """Initialize the template manager.
        
        Args:
            template_dirs: List of directories to load templates from
            cache_size: Maximum number of templates to cache
            cache_ttl: Time-to-live for cache entries in seconds
        """
        self.template_dirs = template_dirs or DEFAULT_TEMPLATE_DIRS
        self.cache = TemplateCache(max_size=cache_size, ttl=cache_ttl)
        self.templates: Dict[str, Dict[str, Any]] = {}
        self.components: Dict[str, str] = {}
        self.loaded = False
        
    def load_templates(self, force_reload: bool = False) -> None:
        """Load all templates from the template directories.
        
        Args:
            force_reload: Whether to force reload even if templates are already loaded
        """
        if self.loaded and not force_reload:
            return
            
        self.templates = {}
        self.components = {}
        
        # Create template directories if they don't exist
        for dir_path in self.template_dirs:
            os.makedirs(dir_path, exist_ok=True)
        
        # Load components first (they may be referenced by templates)
        for dir_path in self.template_dirs:
            component_path = os.path.join(dir_path, "components")
            if os.path.exists(component_path):
                self._load_components_from_dir(component_path)
        
        # Load templates
        for dir_path in self.template_dirs:
            if os.path.exists(dir_path):
                self._load_templates_from_dir(dir_path)
        
        self.loaded = True
        logger.info(f"Loaded {len(self.templates)} templates and {len(self.components)} components")
    
    def _load_templates_from_dir(self, dir_path: str) -> None:
        """Load templates from a directory.
        
        Args:
            dir_path: Directory to load templates from
        """
        for file_path in Path(dir_path).glob("**/*.yaml"):
            if "components" in str(file_path):
                continue  # Skip component files, they're loaded separately
                
            try:
                with open(file_path, 'r') as f:
                    template_data = yaml.safe_load(f)
                
                if not template_data:
                    logger.warning(f"Empty template file: {file_path}")
                    continue
                
                # Extract template metadata and content
                for template_name, template_info in template_data.items():
                    if isinstance(template_info, dict) and "content" in template_info:
                        # Store the template with metadata
                        template_id = f"{os.path.basename(file_path).split('.')[0]}.{template_name}"
                        self.templates[template_id] = template_info
                    else:
                        logger.warning(f"Invalid template format in {file_path}: {template_name}")
            
            except Exception as e:
                logger.error(f"Error loading template from {file_path}: {str(e)}")
    
    def _load_components_from_dir(self, dir_path: str) -> None:
        """Load template components from a directory.
        
        Args:
            dir_path: Directory to load components from
        """
        for file_path in Path(dir_path).glob("**/*.yaml"):
            try:
                with open(file_path, 'r') as f:
                    component_data = yaml.safe_load(f)
                
                if not component_data:
                    logger.warning(f"Empty component file: {file_path}")
                    continue
                
                # Extract component content
                for component_name, component_content in component_data.items():
                    if isinstance(component_content, str):
                        # Store the component
                        self.components[component_name] = component_content
                    else:
                        logger.warning(f"Invalid component format in {file_path}: {component_name}")
            
            except Exception as e:
                logger.error(f"Error loading component from {file_path}: {str(e)}")
    
    def get_template(self, template_id: str) -> Optional[Dict[str, Any]]:
        """Get a template by ID.
        
        Args:
            template_id: Template identifier
            
        Returns:
            Template data or None if not found
        """
        if not self.loaded:
            self.load_templates()
            
        return self.templates.get(template_id)
    
    def get_component(self, component_id: str) -> Optional[str]:
        """Get a template component by ID.
        
        Args:
            component_id: Component identifier
            
        Returns:
            Component content or None if not found
        """
        if not self.loaded:
            self.load_templates()
            
        return self.components.get(component_id)
    
    def _find_component_references(self, template_content: str) -> List[str]:
        """Find component references in a template.
        
        Args:
            template_content: Template content to search
            
        Returns:
            List of component IDs referenced in the template
        """
        # Pattern for component references like {{component:component_name}}
        pattern = r'{{component:([a-zA-Z0-9_.-]+)}}'
        return re.findall(pattern, template_content)
    
    def _replace_components(self, template_content: str) -> str:
        """Replace component references with component content.
        
        Args:
            template_content: Template content with component references
            
        Returns:
            Template with component references replaced
        """
        component_ids = self._find_component_references(template_content)
        
        for component_id in component_ids:
            component_content = self.get_component(component_id)
            if component_content:
                # Recursively process component content (it might contain other components)
                component_content = self._replace_components(component_content)
                template_content = template_content.replace(f"{{{{component:{component_id}}}}}", component_content)
            else:
                logger.warning(f"Component not found: {component_id}")
                # Leave a placeholder for missing components
                template_content = template_content.replace(
                    f"{{{{component:{component_id}}}}}",
                    f"[MISSING COMPONENT: {component_id}]"
                )
        
        return template_content
    
    def _get_cache_key(self, template_id: str, variables: Dict[str, Any]) -> str:
        """Generate a cache key for a template and its variables.
        
        Args:
            template_id: Template identifier
            variables: Template variables
            
        Returns:
            Cache key string
        """
        # Sort variable keys for consistent hashing
        var_str = json.dumps(variables, sort_keys=True)
        return f"{template_id}:{hashlib.md5(var_str.encode()).hexdigest()}"
    
    def render_template(self, template_id: str, variables: Dict[str, Any] = None) -> str:
        """Render a template with the given variables.
        
        Args:
            template_id: Template identifier
            variables: Variables to substitute in the template
            
        Returns:
            Rendered template
            
        Raises:
            ValueError: If template not found
        """
        variables = variables or {}
        
        # Check cache first
        cache_key = self._get_cache_key(template_id, variables)
        cached_template = self.cache.get(cache_key)
        if cached_template:
            return cached_template
        
        # Get the template
        template_data = self.get_template(template_id)
        if not template_data:
            raise ValueError(f"Template not found: {template_id}")
        
        # Get the template content
        template_content = template_data.get("content", "")
        if not template_content:
            logger.warning(f"Empty template content for {template_id}")
            return ""
        
        # Replace components
        template_content = self._replace_components(template_content)
        
        # Substitute variables
        try:
            # Gracefully handle missing variables and format errors
            for attempt in range(2):
                try:
                    # First attempt: use strict formatting
                    if attempt == 0:
                        template_content = template_content.format(**variables)
                        break
                    # Second attempt: use placeholder for missing variables
                    else:
                        class MissingDict(dict):
                            def __missing__(self, key):
                                return f"[{key}]"
                        template_content = template_content.format_map(MissingDict(variables))
                except (KeyError, ValueError, IndexError) as e:
                    if attempt == 0:
                        logger.warning(f"Template formatting error in {template_id}: {str(e)}, falling back to placeholder mode")
                    else:
                        logger.error(f"Template formatting error in {template_id}: {str(e)}")
                        template_content = f"Error rendering template {template_id}: {str(e)}"
        except Exception as e:
            logger.error(f"Unexpected error rendering template {template_id}: {str(e)}")
            template_content = f"Error rendering template {template_id}: {str(e)}"
        
        # Cache the rendered template
        self.cache.set(cache_key, template_content)
        
        return template_content
    
    def detect_scenario(self, context: Dict[str, Any]) -> str:
        """Detect the appropriate scenario for template selection.
        
        This is a placeholder for a more sophisticated scenario detection mechanism.
        In a real implementation, this would analyze the context to determine the most
        appropriate template scenario.
        
        Args:
            context: Context information for scenario detection
            
        Returns:
            Detected scenario identifier
        """
        # Extract relevant information from the context
        conversation_stage = context.get("conversation_stage", "understanding")
        intent = context.get("intent", "general")
        agent_type = context.get("agent_type", "default")
        
        # Simple mapping logic (to be replaced with more sophisticated detection)
        if conversation_stage == "understanding":
            if intent == "code_generation":
                return "code_understanding"
            elif intent == "research":
                return "research_understanding"
            else:
                return "general_understanding"
        elif conversation_stage == "planning":
            return f"{agent_type}_planning"
        elif conversation_stage == "execution":
            return f"{agent_type}_execution"
        else:
            return "default"
    
    def get_template_for_scenario(self, scenario: str) -> Optional[str]:
        """Get the appropriate template ID for a scenario.
        
        Args:
            scenario: Scenario identifier
            
        Returns:
            Template ID or None if no matching template
        """
        # In a real implementation, this would use a mapping of scenarios to templates
        # For now, we'll use a simple naming convention
        template_id = f"scenarios.{scenario}"
        
        if template_id in self.templates:
            return template_id
        
        # Fall back to default if specific scenario not found
        fallback_id = "scenarios.default"
        if fallback_id in self.templates:
            logger.warning(f"Scenario template not found for {scenario}, using default")
            return fallback_id
        
        logger.error(f"No template found for scenario {scenario} and no default available")
        return None
    
    def render_for_scenario(self, context: Dict[str, Any], variables: Dict[str, Any] = None) -> Optional[str]:
        """Detect scenario and render the appropriate template.
        
        Args:
            context: Context information for scenario detection
            variables: Variables to substitute in the template
            
        Returns:
            Rendered template or None if no suitable template found
        """
        scenario = self.detect_scenario(context)
        template_id = self.get_template_for_scenario(scenario)
        
        if template_id:
            # Merge context and variables
            merged_vars = {**context, **(variables or {})}
            return self.render_template(template_id, merged_vars)
        
        return None


# Singleton instance
_template_manager = None

def get_template_manager() -> TemplateManager:
    """Get the singleton template manager instance.
    
    Returns:
        Template manager instance
    """
    global _template_manager
    
    if _template_manager is None:
        _template_manager = TemplateManager()
        
    return _template_manager 