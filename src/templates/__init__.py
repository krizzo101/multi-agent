"""
Prompt Template System for the Multi-Agent Framework.

This package provides a flexible template system for managing and rendering
prompt templates used by agents. It supports variable substitution, template
assembly, and scenario-based template selection.
"""

from .manager import (
    TemplateManager,
    TemplateCache,
    get_template_manager,
)

__all__ = [
    'TemplateManager',
    'TemplateCache',
    'get_template_manager',
] 