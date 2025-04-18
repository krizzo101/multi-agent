"""
Agent Templates Utility

Provides a template system for agent profiles to enable efficient customization
of agent configurations based on predefined templates, allowing the dynamic proxy
to quickly configure specialized agents without regenerating all details.
"""

import os
import yaml
import json
import logging
import time
from typing import Dict, Any, List, Optional, Tuple, Set
from pathlib import Path

logger = logging.getLogger(__name__)

class AgentTemplate:
    """
    Represents a template for an agent profile that can be customized.
    
    Templates contain base configurations for different types of agents
    that can be specialized for specific domains or tasks.
    """
    
    def __init__(
        self,
        template_id: str,
        name: str,
        description: str,
        base_system_message: str,
        expertise_areas: List[str] = None,
        temperature_range: Tuple[float, float] = (0.1, 0.7),
        supported_tools: List[str] = None,
        prompt_preamble: str = "",
        template_variables: List[str] = None,
    ):
        """
        Initialize an agent template.
        
        Args:
            template_id: Unique identifier for the template
            name: Display name for the template
            description: Description of the template's purpose and use case
            base_system_message: Base system message that can be customized
            expertise_areas: Areas of expertise this template is designed for
            temperature_range: Range of valid temperature values (min, max)
            supported_tools: List of tool IDs that work well with this template
            prompt_preamble: Optional preamble to add to user queries
            template_variables: Variables that can be used for customization
        """
        self.template_id = template_id
        self.name = name
        self.description = description
        self.base_system_message = base_system_message
        self.expertise_areas = expertise_areas or []
        self.temperature_range = temperature_range
        self.supported_tools = supported_tools or []
        self.prompt_preamble = prompt_preamble
        self.template_variables = template_variables or []
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert template to dictionary for serialization."""
        return {
            "template_id": self.template_id,
            "name": self.name,
            "description": self.description,
            "base_system_message": self.base_system_message,
            "expertise_areas": self.expertise_areas,
            "temperature_range": self.temperature_range,
            "supported_tools": self.supported_tools,
            "prompt_preamble": self.prompt_preamble,
            "template_variables": self.template_variables,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'AgentTemplate':
        """Create template from dictionary."""
        return cls(
            template_id=data["template_id"],
            name=data["name"],
            description=data["description"],
            base_system_message=data["base_system_message"],
            expertise_areas=data.get("expertise_areas", []),
            temperature_range=tuple(data.get("temperature_range", (0.1, 0.7))),
            supported_tools=data.get("supported_tools", []),
            prompt_preamble=data.get("prompt_preamble", ""),
            template_variables=data.get("template_variables", []),
        )
    
    def customize(self, variables: Dict[str, Any]) -> Dict[str, Any]:
        """
        Customize this template with specific values.
        
        Args:
            variables: Dictionary of variable values for customization
            
        Returns:
            Customized agent configuration
        """
        # Start with a base configuration
        config = {
            "agent_id": f"dynamic_{self.template_id}_{int(time.time())}",
            "name": self.name,
            "description": self.description,
            "expertise_areas": self.expertise_areas.copy(),
            "system_message": self.base_system_message,
            "temperature": self.temperature_range[0],  # Default to lower end
            "prompt_preamble": self.prompt_preamble,
            "tools": self.supported_tools.copy(),
            "additional_context": {}
        }
        
        # Apply variable customizations
        for var, value in variables.items():
            if var == "expertise_domains" and isinstance(value, list):
                config["expertise_areas"].extend(value)
            elif var == "specialization":
                config["name"] = f"{value} {self.name}"
                config["system_message"] = config["system_message"].replace(
                    "{specialization}", value
                )
            elif var == "temperature" and isinstance(value, (int, float)):
                min_temp, max_temp = self.temperature_range
                config["temperature"] = max(min_temp, min(max_temp, value))
            elif var == "tools" and isinstance(value, list):
                # Add tools but keep only those that are supported
                config["tools"] = list(set(config["tools"]) | set(value))
            elif var == "domain_knowledge" and isinstance(value, str):
                config["additional_context"]["domain_knowledge"] = value
            elif var == "task_description" and isinstance(value, str):
                config["additional_context"]["task_description"] = value
            elif var == "additional_instructions" and isinstance(value, str):
                # Append to system message
                config["system_message"] += f"\n\n{value}"
            elif var == "examples" and isinstance(value, list):
                # Add examples to additional context
                config["additional_context"]["examples"] = value
        
        # Clean up template variables in system message
        for var in self.template_variables:
            config["system_message"] = config["system_message"].replace(
                f"{{{var}}}", ""
            ).replace(f" {{}}", "")
        
        return config


class AgentTemplateCache:
    """Cache for recently used agent templates and configurations."""
    
    def __init__(self, max_size: int = 10):
        """
        Initialize the template cache.
        
        Args:
            max_size: Maximum number of configurations to cache
        """
        self.max_size = max_size
        self.recent_configs: Dict[str, Dict[str, Any]] = {}
        self.access_times: Dict[str, float] = {}
    
    def add(self, query_hash: str, config: Dict[str, Any]) -> None:
        """
        Add a configuration to the cache.
        
        Args:
            query_hash: Hash of the query that generated this config
            config: Agent configuration to cache
        """
        # If cache is full, remove least recently used entry
        if len(self.recent_configs) >= self.max_size:
            # Find least recently accessed item
            lru_key = min(self.access_times.items(), key=lambda x: x[1])[0]
            del self.recent_configs[lru_key]
            del self.access_times[lru_key]
        
        # Add new entry
        self.recent_configs[query_hash] = config
        self.access_times[query_hash] = time.time()
    
    def get(self, query_hash: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve a configuration from the cache.
        
        Args:
            query_hash: Hash of the query
            
        Returns:
            Cached configuration or None if not found
        """
        if query_hash in self.recent_configs:
            # Update access time
            self.access_times[query_hash] = time.time()
            return self.recent_configs[query_hash]
        return None
    
    def clear(self) -> None:
        """Clear the cache."""
        self.recent_configs.clear()
        self.access_times.clear()


class AgentTemplateManager:
    """
    Manager for agent templates and tool configurations.
    
    This class handles loading templates from files, customizing templates,
    and selecting appropriate templates based on queries.
    """
    
    def __init__(self, templates_dir: Optional[str] = None):
        """
        Initialize the template manager.
        
        Args:
            templates_dir: Optional custom directory for templates
        """
        # Set up template directory
        if templates_dir:
            self.templates_dir = Path(templates_dir)
        else:
            # Default to src/agents/templates
            base_dir = Path(__file__).parent.parent
            self.templates_dir = base_dir / "templates"
        
        # Create directory if it doesn't exist
        os.makedirs(self.templates_dir, exist_ok=True)
        
        # Initialize template storage
        self.templates: Dict[str, AgentTemplate] = {}
        self.tools_config: Dict[str, Dict[str, Any]] = {}
        
        # Initialize cache
        self.cache = AgentTemplateCache()
        
        # Load templates
        self.load_templates()
    
    def load_templates(self, force_reload: bool = False) -> None:
        """
        Load all templates from disk.
        
        Args:
            force_reload: Force reload even if already loaded
        """
        if self.templates and not force_reload:
            return
        
        # Clear existing templates
        self.templates = {}
        self.tools_config = {}
        
        try:
            # Load agent templates
            templates_file = self.templates_dir / "agent_templates.yaml"
            if templates_file.exists():
                with open(templates_file, 'r') as f:
                    templates_data = yaml.safe_load(f) or {}
                
                for template_id, template_data in templates_data.items():
                    try:
                        self.templates[template_id] = AgentTemplate.from_dict({
                            "template_id": template_id,
                            **template_data
                        })
                    except Exception as e:
                        logger.error(f"Error loading template {template_id}: {str(e)}")
            else:
                # Create default templates file
                self._create_default_templates()
            
            # Load tools configuration
            tools_file = self.templates_dir / "tools_config.yaml"
            if tools_file.exists():
                with open(tools_file, 'r') as f:
                    self.tools_config = yaml.safe_load(f) or {}
            else:
                # Create default tools config
                self._create_default_tools_config()
            
            logger.info(f"Loaded {len(self.templates)} agent templates and {len(self.tools_config)} tool configurations")
        
        except Exception as e:
            logger.error(f"Error loading templates: {str(e)}", exc_info=True)
    
    def _create_default_templates(self) -> None:
        """Create default agent templates if none exist."""
        default_templates = {
            "developer": {
                "name": "Developer",
                "description": "Specialized in software development, coding, and technical problem-solving",
                "base_system_message": """You are an experienced {specialization} Developer with deep expertise in software development, architecture, and technical problem-solving.

Your primary goal is to provide high-quality, well-structured, and efficient code solutions that follow best practices.

When writing code:
- Focus on readability, maintainability, and performance
- Include appropriate error handling and input validation
- Follow language-specific conventions and best practices
- Optimize for the specific use case while maintaining clean code principles

When explaining concepts:
- Break down complex topics into clear, understandable explanations
- Provide context and examples to illustrate key points
- Highlight potential pitfalls and edge cases
- Reference established patterns and principles when relevant

{additional_instructions}""",
                "expertise_areas": ["programming", "software development", "debugging", "code optimization"],
                "temperature_range": [0.1, 0.4],
                "supported_tools": ["code_analysis", "unit_test_generation", "code_completion"],
                "template_variables": ["specialization", "additional_instructions"]
            },
            "data_scientist": {
                "name": "Data Scientist",
                "description": "Specialized in data analysis, statistical modeling, and machine learning",
                "base_system_message": """You are an experienced {specialization} Data Scientist with expertise in data analysis, statistical modeling, and machine learning.

Your primary goal is to provide insightful analysis and solutions to data-related problems using rigorous methodologies.

When analyzing data:
- Focus on understanding the underlying patterns and relationships
- Use appropriate statistical methods and validation techniques
- Consider potential biases and limitations in the data
- Provide clear interpretations of results and their implications

When developing models:
- Select appropriate algorithms based on the problem and data characteristics
- Balance model complexity, performance, and interpretability
- Validate results using appropriate metrics and cross-validation
- Consider practical implementation considerations

{additional_instructions}""",
                "expertise_areas": ["data analysis", "statistics", "machine learning", "data visualization"],
                "temperature_range": [0.1, 0.5],
                "supported_tools": ["data_analysis", "visualization", "model_evaluation"],
                "template_variables": ["specialization", "additional_instructions"]
            },
            "researcher": {
                "name": "Researcher",
                "description": "Specialized in academic research, literature review, and knowledge synthesis",
                "base_system_message": """You are a thorough {specialization} Researcher with expertise in analyzing information, synthesizing knowledge, and providing well-founded insights.

Your primary goal is to provide comprehensive, accurate, and nuanced information based on established research and reliable sources.

When researching topics:
- Focus on credible, up-to-date information from reliable sources
- Consider multiple perspectives and competing theories
- Distinguish between established facts, scholarly consensus, and areas of ongoing debate
- Acknowledge limitations in current knowledge and uncertainties

When presenting findings:
- Organize information logically with clear structure
- Provide context to help understand the significance of information
- Balance depth and breadth appropriate to the query
- Cite or reference sources when making specific claims

{additional_instructions}""",
                "expertise_areas": ["research methodology", "literature review", "academic writing", "critical analysis"],
                "temperature_range": [0.1, 0.3],
                "supported_tools": ["literature_search", "citation_analysis", "knowledge_synthesis"],
                "template_variables": ["specialization", "additional_instructions"]
            },
            "strategic_advisor": {
                "name": "Strategic Advisor",
                "description": "Specialized in business strategy, decision analysis, and problem-solving",
                "base_system_message": """You are an insightful {specialization} Strategic Advisor with expertise in business strategy, decision analysis, and problem-solving.

Your primary goal is to provide thoughtful, balanced, and actionable advice on complex strategic issues.

When analyzing strategic problems:
- Consider multiple stakeholder perspectives and potential impacts
- Evaluate short-term and long-term implications
- Assess risks, uncertainties, and potential unintended consequences
- Balance idealism with pragmatism and feasibility

When providing recommendations:
- Offer clear, actionable advice with supporting rationale
- Present multiple options when appropriate, with pros and cons
- Consider implementation challenges and potential mitigations
- Tailor advice to the specific context and constraints

{additional_instructions}""",
                "expertise_areas": ["business strategy", "decision analysis", "problem-solving", "risk assessment"],
                "temperature_range": [0.2, 0.6],
                "supported_tools": ["decision_analysis", "risk_assessment", "scenario_planning"],
                "template_variables": ["specialization", "additional_instructions"]
            },
            "creative": {
                "name": "Creative",
                "description": "Specialized in creative writing, content creation, and ideation",
                "base_system_message": """You are a versatile {specialization} Creative with expertise in generating original, engaging, and high-quality creative content.

Your primary goal is to produce content that is original, engaging, and tailored to the specific needs and context.

When creating content:
- Focus on originality, engagement, and quality
- Adapt your tone, style, and approach to the specific purpose and audience
- Balance creativity with practicality and relevance
- Consider emotional impact and resonance

When brainstorming ideas:
- Generate diverse options that explore different directions
- Consider novel combinations and unexpected perspectives
- Evaluate ideas based on relevance, feasibility, and potential impact
- Refine promising concepts with attention to detail

{additional_instructions}""",
                "expertise_areas": ["creative writing", "content creation", "ideation", "storytelling"],
                "temperature_range": [0.5, 0.9],
                "supported_tools": ["content_generation", "creative_writing", "ideation"],
                "template_variables": ["specialization", "additional_instructions"]
            }
        }
        
        # Save default templates
        templates_file = self.templates_dir / "agent_templates.yaml"
        with open(templates_file, 'w') as f:
            yaml.dump(default_templates, f, default_flow_style=False)
        
        # Load the templates
        for template_id, template_data in default_templates.items():
            self.templates[template_id] = AgentTemplate.from_dict({
                "template_id": template_id,
                **template_data
            })
        
        logger.info(f"Created default agent templates: {', '.join(default_templates.keys())}")
    
    def _create_default_tools_config(self) -> None:
        """Create default tools configuration if none exists."""
        default_tools_config = {
            "code_analysis": {
                "description": "Analyzes code to identify patterns, issues, and optimization opportunities",
                "parameters": ["language", "code_snippet", "analysis_type"],
                "compatible_with": ["developer", "data_scientist"],
                "temperature_adjustment": -0.1
            },
            "unit_test_generation": {
                "description": "Generates unit tests for given code",
                "parameters": ["language", "code_snippet", "testing_framework"],
                "compatible_with": ["developer"],
                "temperature_adjustment": -0.2
            },
            "data_analysis": {
                "description": "Analyzes data to identify patterns, trends, and insights",
                "parameters": ["data_format", "analysis_type", "visualization_type"],
                "compatible_with": ["data_scientist", "researcher"],
                "temperature_adjustment": -0.1
            },
            "literature_search": {
                "description": "Searches academic literature for relevant information",
                "parameters": ["topic", "keywords", "max_results"],
                "compatible_with": ["researcher", "data_scientist"],
                "temperature_adjustment": -0.1
            },
            "decision_analysis": {
                "description": "Analyzes decision options and their implications",
                "parameters": ["options", "criteria", "constraints"],
                "compatible_with": ["strategic_advisor"],
                "temperature_adjustment": 0.0
            },
            "content_generation": {
                "description": "Generates creative content based on specifications",
                "parameters": ["content_type", "style", "length", "tone"],
                "compatible_with": ["creative"],
                "temperature_adjustment": 0.2
            }
        }
        
        # Save default tools config
        tools_file = self.templates_dir / "tools_config.yaml"
        with open(tools_file, 'w') as f:
            yaml.dump(default_tools_config, f, default_flow_style=False)
        
        self.tools_config = default_tools_config
        logger.info(f"Created default tools configuration: {', '.join(default_tools_config.keys())}")
    
    def get_template(self, template_id: str) -> Optional[AgentTemplate]:
        """
        Get a template by ID.
        
        Args:
            template_id: ID of the template to retrieve
            
        Returns:
            Template instance or None if not found
        """
        return self.templates.get(template_id)
    
    def get_tool_config(self, tool_id: str) -> Optional[Dict[str, Any]]:
        """
        Get configuration for a specific tool.
        
        Args:
            tool_id: ID of the tool to retrieve
            
        Returns:
            Tool configuration or None if not found
        """
        return self.tools_config.get(tool_id)
    
    def get_compatible_tools(self, template_id: str) -> List[str]:
        """
        Get tools compatible with a specific template.
        
        Args:
            template_id: ID of the template
            
        Returns:
            List of compatible tool IDs
        """
        compatible_tools = []
        for tool_id, tool_config in self.tools_config.items():
            if template_id in tool_config.get("compatible_with", []):
                compatible_tools.append(tool_id)
        return compatible_tools
    
    def customize_template(
        self,
        template_id: str,
        variables: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        Customize a template with specific values.
        
        Args:
            template_id: ID of the template to customize
            variables: Customization variables
            
        Returns:
            Customized agent configuration or None if template not found
        """
        template = self.get_template(template_id)
        if not template:
            logger.error(f"Template not found: {template_id}")
            return None
        
        return template.customize(variables)
    
    def find_best_template(
        self,
        analysis: Dict[str, Any]
    ) -> Tuple[str, Dict[str, Any]]:
        """
        Find the best template for a given query analysis.
        
        Args:
            analysis: Analysis of the user query
            
        Returns:
            Tuple of (template_id, customization_variables)
        """
        # Extract key information from analysis
        intent = analysis.get("primary_intent", "").lower()
        domains = analysis.get("domains", [])
        entities = analysis.get("entities", [])
        complexity = analysis.get("complexity", 3)
        
        # Default to 'researcher' if we can't determine a good match
        best_template_id = "researcher"
        best_score = 0
        
        # Score each template
        for template_id, template in self.templates.items():
            score = 0
            
            # Check if template expertise areas match any domains or entities
            expertise_areas = set(area.lower() for area in template.expertise_areas)
            for domain in domains:
                if domain.lower() in expertise_areas:
                    score += 2
            
            for entity in entities:
                if entity.lower() in expertise_areas:
                    score += 1
            
            # Check if intent aligns with template purpose
            if "code" in intent or "program" in intent or "develop" in intent:
                if template_id == "developer":
                    score += 3
            elif "data" in intent or "analyze" in intent or "predict" in intent:
                if template_id == "data_scientist":
                    score += 3
            elif "research" in intent or "learn" in intent or "understand" in intent:
                if template_id == "researcher":
                    score += 3
            elif "strategy" in intent or "decide" in intent or "plan" in intent:
                if template_id == "strategic_advisor":
                    score += 3
            elif "create" in intent or "write" in intent or "design" in intent:
                if template_id == "creative":
                    score += 3
            
            # Update best match if higher score
            if score > best_score:
                best_template_id = template_id
                best_score = score
        
        # Determine specialization
        specialization = ""
        if domains:
            specialization = domains[0].title()
        elif entities:
            specialization = entities[0].title()
        
        # Build customization variables
        variables = {
            "specialization": specialization,
            "expertise_domains": domains + entities,
            "temperature": 0.1 + (complexity * 0.1),  # Scale based on complexity
        }
        
        # Get compatible tools
        variables["tools"] = self.get_compatible_tools(best_template_id)
        
        # Add task description if available
        if "query" in analysis:
            variables["task_description"] = analysis["query"]
        
        return best_template_id, variables
    
    def save_template(self, template: AgentTemplate) -> None:
        """
        Save a new or updated template.
        
        Args:
            template: Template to save
        """
        # Add to memory
        self.templates[template.template_id] = template
        
        # Save to disk
        templates_file = self.templates_dir / "agent_templates.yaml"
        
        try:
            # Load existing templates
            if templates_file.exists():
                with open(templates_file, 'r') as f:
                    templates_data = yaml.safe_load(f) or {}
            else:
                templates_data = {}
            
            # Update with new template
            templates_data[template.template_id] = {
                k: v for k, v in template.to_dict().items() if k != "template_id"
            }
            
            # Save back to file
            with open(templates_file, 'w') as f:
                yaml.dump(templates_data, f, default_flow_style=False)
            
            logger.info(f"Saved template: {template.template_id}")
        
        except Exception as e:
            logger.error(f"Error saving template {template.template_id}: {str(e)}")
    
    def delete_template(self, template_id: str) -> bool:
        """
        Delete a template.
        
        Args:
            template_id: ID of the template to delete
            
        Returns:
            True if deleted, False if not found
        """
        if template_id not in self.templates:
            return False
        
        # Remove from memory
        del self.templates[template_id]
        
        # Remove from disk
        templates_file = self.templates_dir / "agent_templates.yaml"
        
        try:
            # Load existing templates
            if templates_file.exists():
                with open(templates_file, 'r') as f:
                    templates_data = yaml.safe_load(f) or {}
                
                # Remove template
                if template_id in templates_data:
                    del templates_data[template_id]
                
                # Save back to file
                with open(templates_file, 'w') as f:
                    yaml.dump(templates_data, f, default_flow_style=False)
            
            logger.info(f"Deleted template: {template_id}")
            return True
        
        except Exception as e:
            logger.error(f"Error deleting template {template_id}: {str(e)}")
            return False
    
    def compute_query_hash(self, query: str, context_id: str = "") -> str:
        """
        Compute a hash for a query to use as a cache key.
        
        Args:
            query: User query
            context_id: Optional context identifier
            
        Returns:
            Hash string for the query
        """
        import hashlib
        # Create a hash of query + context ID
        combined = f"{query}:{context_id}"
        return hashlib.md5(combined.encode()).hexdigest()
    
    def get_cached_config(self, query: str, context_id: str = "") -> Optional[Dict[str, Any]]:
        """
        Get a cached configuration for a similar query.
        
        Args:
            query: User query
            context_id: Optional context identifier
            
        Returns:
            Cached configuration or None if not found
        """
        query_hash = self.compute_query_hash(query, context_id)
        return self.cache.get(query_hash)
    
    def cache_config(self, query: str, config: Dict[str, Any], context_id: str = "") -> None:
        """
        Cache a configuration for future use.
        
        Args:
            query: User query that generated this config
            config: Agent configuration to cache
            context_id: Optional context identifier
        """
        query_hash = self.compute_query_hash(query, context_id)
        self.cache.add(query_hash, config)


# Global instance for singleton access
_template_manager = None

def get_template_manager() -> AgentTemplateManager:
    """
    Get the global template manager instance.
    
    Returns:
        Global template manager instance
    """
    global _template_manager
    if _template_manager is None:
        _template_manager = AgentTemplateManager()
    return _template_manager 