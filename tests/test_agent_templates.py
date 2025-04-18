#!/usr/bin/env python3
"""
Tests for the agent template system.

This script demonstrates and tests the agent template system, showing
how templates are selected, customized, and used.
"""

import os
import sys
import json
import logging
from typing import Dict, Any

# Add the repo root to the path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.agents.utils import get_template_manager, QueryAnalyzer

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def print_heading(text: str):
    """Print a formatted heading."""
    print("\n" + "=" * 80)
    print(f" {text}")
    print("=" * 80)

def print_json(data: Dict[str, Any]):
    """Print formatted JSON data."""
    print(json.dumps(data, indent=2))

def test_template_selection():
    """Test template selection based on query analysis."""
    print_heading("Testing Template Selection")
    
    # Get template manager
    template_manager = get_template_manager()
    
    # Test queries
    test_queries = [
        {
            "query": "How do I fix a memory leak in my Python code?",
            "expected_template": "developer"
        },
        {
            "query": "Can you analyze this dataset and create a visualization?",
            "expected_template": "data_scientist"
        },
        {
            "query": "What are the latest research papers on quantum computing?",
            "expected_template": "researcher"
        },
        {
            "query": "Help me develop a business strategy for my startup.",
            "expected_template": "strategic_advisor"
        },
        {
            "query": "Write a creative story about a space explorer.",
            "expected_template": "creative"
        }
    ]
    
    # Test each query
    analyzer = QueryAnalyzer()
    
    for test in test_queries:
        query = test["query"]
        expected = test["expected_template"]
        
        # Analyze query
        analysis = analyzer.analyze_query(query)
        
        # Find best template
        template_id, variables = template_manager.find_best_template(analysis)
        
        # Print results
        print(f"\nQuery: {query}")
        print(f"Analysis: {analysis.get('primary_intent')}, complexity: {analysis.get('complexity')}")
        print(f"Selected template: {template_id} (expected: {expected})")
        
        # Verify template exists
        template = template_manager.get_template(template_id)
        if template:
            print(f"Template found: {template.name}")
        else:
            print(f"ERROR: Template not found: {template_id}")

def test_template_customization():
    """Test customizing templates with variables."""
    print_heading("Testing Template Customization")
    
    # Get template manager
    template_manager = get_template_manager()
    
    # Test template customization
    template_id = "developer"
    customization_vars = {
        "specialization": "Python",
        "expertise_domains": ["web development", "data processing"],
        "temperature": 0.2,
        "additional_instructions": "Focus on writing maintainable and efficient code."
    }
    
    # Get the template
    template = template_manager.get_template(template_id)
    if not template:
        print(f"ERROR: Template not found: {template_id}")
        return
    
    print(f"Customizing template: {template.name}")
    print(f"Original template expertise areas: {template.expertise_areas}")
    print(f"Customization variables: {customization_vars}")
    
    # Customize template
    config = template_manager.customize_template(template_id, customization_vars)
    
    if not config:
        print("ERROR: Customization failed")
        return
    
    # Print key parts of the result
    print("\nCustomized configuration:")
    print(f"Name: {config['name']}")
    print(f"Expertise areas: {config['expertise_areas']}")
    print(f"Temperature: {config['temperature']}")
    print(f"Tools: {config.get('tools', [])}")
    
    # Show how system message was customized
    system_message_lines = config['system_message'].strip().split('\n')
    first_line = system_message_lines[0]
    last_line = system_message_lines[-1]
    print(f"System message first line: {first_line}")
    print(f"System message last line: {last_line}")

def test_template_caching():
    """Test caching of agent configurations."""
    print_heading("Testing Template Caching")
    
    # Get template manager
    template_manager = get_template_manager()
    
    # Clear cache to start fresh
    template_manager.cache.clear()
    
    # Test query
    query = "How do I implement a binary search tree in Java?"
    session_id = "test-session-123"
    
    # Analyze query
    analyzer = QueryAnalyzer()
    analysis = analyzer.analyze_query(query)
    
    # Find best template and customize
    template_id, variables = template_manager.find_best_template(analysis)
    config = template_manager.customize_template(template_id, variables)
    
    if not config:
        print("ERROR: Customization failed")
        return
    
    print(f"Created configuration for: {query}")
    print(f"Template ID: {template_id}")
    
    # Cache the configuration
    template_manager.cache_config(query, config, session_id)
    
    # Check if cache works
    cached_config = template_manager.get_cached_config(query, session_id)
    if cached_config:
        print("SUCCESS: Configuration was cached and retrieved")
    else:
        print("ERROR: Configuration was not cached")
    
    # Try a similar query
    similar_query = "Can you show me how to implement a binary search tree in Java?"
    cached_config = template_manager.get_cached_config(similar_query, session_id)
    
    if cached_config:
        print("ERROR: Cache should not match for different queries")
    else:
        print("SUCCESS: Cache correctly doesn't match for different queries")
    
    # Cache the configuration with the similar query
    template_manager.cache_config(similar_query, config, session_id)
    
    # Check exact query match
    cached_config = template_manager.get_cached_config(similar_query, session_id)
    if cached_config:
        print("SUCCESS: Configuration was cached and retrieved for similar query")
    else:
        print("ERROR: Configuration was not cached for similar query")

def test_tool_configurations():
    """Test tool configurations and compatibility."""
    print_heading("Testing Tool Configurations")
    
    # Get template manager
    template_manager = get_template_manager()
    
    # List all templates
    print("Available templates:")
    for template_id, template in template_manager.templates.items():
        print(f"  - {template_id}: {template.name}")
    
    # For each template, show compatible tools
    for template_id, template in template_manager.templates.items():
        compatible_tools = template_manager.get_compatible_tools(template_id)
        
        print(f"\nCompatible tools for {template.name}:")
        for tool_id in compatible_tools:
            tool_config = template_manager.get_tool_config(tool_id)
            if tool_config:
                print(f"  - {tool_id}: {tool_config['description']}")
                print(f"    Temperature adjustment: {tool_config.get('temperature_adjustment', 0.0)}")

def main():
    """Run all tests."""
    try:
        print_heading("AGENT TEMPLATE SYSTEM TESTS")
        
        # Run tests
        test_template_selection()
        test_template_customization()
        test_template_caching()
        test_tool_configurations()
        
        print_heading("All tests completed")
        
    except Exception as e:
        logger.error(f"Error during tests: {str(e)}", exc_info=True)
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main()) 