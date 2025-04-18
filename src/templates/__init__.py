"""
Prompt Template System for the Multi-Agent Framework.

This package provides a flexible template system for managing and rendering
prompt templates used by agents. It supports variable substitution, template
assembly, and scenario-based template selection.
"""

import logging
from .manager import (
    TemplateManager,
    TemplateCache,
    get_template_manager,
)

logger = logging.getLogger(__name__)

# Initialize the template system on import
try:
    # Initialize but don't log details
    template_manager = get_template_manager()
    template_manager.load_templates(force_reload=True)
except Exception as e:
    logger.error(f"Error initializing template system: {str(e)}", exc_info=True)

# Make sure all components are exported
__all__ = [
    'TemplateManager',
    'TemplateCache',
    'get_template_manager',
] 