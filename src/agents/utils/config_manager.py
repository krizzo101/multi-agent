"""
Configuration Manager Utility

Provides utilities for managing agent configurations, settings, and environment variables.
Supports loading from different sources (env files, JSON, YAML) and provides validation.
"""

import os
import json
import logging
import yaml
from typing import Dict, Any, Optional, List, Union, Set
from pathlib import Path

logger = logging.getLogger(__name__)


class ConfigValidationError(Exception):
    """Exception raised for configuration validation errors."""
    pass


class ConfigManager:
    """
    Manages configuration settings for all agents in the system.
    Handles loading, validation, and access to configuration values.
    """
    
    def __init__(self, config_dir: Optional[str] = None):
        """
        Initialize the configuration manager.
        
        Args:
            config_dir: Directory containing configuration files
        """
        self.config_dir = config_dir or os.path.join(os.path.dirname(__file__), '../../../config')
        self.settings = {
            "global": {},
            "agents": {},
            "llm_providers": {},
            "tools": {},
            "security": {},
            "logging": {},
        }
        self.env_vars = {}
        self.loaded_files = set()
    
    def load_from_env(self, prefix: str = "AGENT_") -> None:
        """
        Load configuration from environment variables.
        
        Args:
            prefix: Prefix for environment variables to load
        """
        for key, value in os.environ.items():
            if key.startswith(prefix):
                # Convert to lowercase and remove prefix for consistency
                config_key = key[len(prefix):].lower()
                self.env_vars[config_key] = value
                
                # Try to parse JSON values
                if value.startswith('{') or value.startswith('['):
                    try:
                        self.env_vars[config_key] = json.loads(value)
                    except json.JSONDecodeError:
                        # Keep as string if not valid JSON
                        pass
                # Convert boolean strings
                elif value.lower() in ('true', 'false'):
                    self.env_vars[config_key] = value.lower() == 'true'
                # Convert numeric strings
                elif value.isdigit():
                    self.env_vars[config_key] = int(value)
                elif self._is_float(value):
                    self.env_vars[config_key] = float(value)
        
        logger.debug(f"Loaded {len(self.env_vars)} environment variables with prefix {prefix}")
    
    def _is_float(self, value: str) -> bool:
        """Check if a string can be converted to float."""
        try:
            float(value)
            return True
        except ValueError:
            return False
    
    def load_file(self, filepath: str) -> Dict[str, Any]:
        """
        Load a configuration file.
        
        Args:
            filepath: Path to the configuration file
            
        Returns:
            Loaded configuration as dictionary
        """
        filepath = os.path.abspath(os.path.join(self.config_dir, filepath)
                                  if not os.path.isabs(filepath) else filepath)
        
        if filepath in self.loaded_files:
            logger.debug(f"Config file already loaded: {filepath}")
            return {}
            
        if not os.path.exists(filepath):
            logger.warning(f"Config file not found: {filepath}")
            return {}
            
        file_ext = os.path.splitext(filepath)[1].lower()
        config_data = {}
        
        try:
            with open(filepath, 'r') as file:
                if file_ext == '.json':
                    config_data = json.load(file)
                elif file_ext in ('.yaml', '.yml'):
                    config_data = yaml.safe_load(file)
                else:
                    logger.warning(f"Unsupported config file format: {file_ext}")
                    return {}
                    
            self.loaded_files.add(filepath)
            logger.info(f"Loaded configuration from {filepath}")
            return config_data
            
        except Exception as e:
            logger.error(f"Error loading config file {filepath}: {str(e)}")
            return {}
    
    def load_configs(self) -> None:
        """Load all configuration files from the config directory."""
        if not os.path.exists(self.config_dir):
            logger.warning(f"Config directory not found: {self.config_dir}")
            return
            
        # Load global config first
        global_config = self.load_file(os.path.join(self.config_dir, 'config.yaml'))
        if global_config:
            self.settings['global'] = global_config.get('global', {})
            
            # Load other top-level sections
            for section in ['agents', 'llm_providers', 'tools', 'security', 'logging']:
                if section in global_config:
                    self.settings[section] = global_config[section]
        
        # Load agent-specific configs
        agents_dir = os.path.join(self.config_dir, 'agents')
        if os.path.exists(agents_dir) and os.path.isdir(agents_dir):
            for filename in os.listdir(agents_dir):
                if filename.endswith(('.yaml', '.yml', '.json')):
                    agent_id = os.path.splitext(filename)[0]
                    agent_config = self.load_file(os.path.join(agents_dir, filename))
                    if agent_config:
                        self.settings['agents'][agent_id] = agent_config
        
        # Load provider-specific configs
        providers_dir = os.path.join(self.config_dir, 'providers')
        if os.path.exists(providers_dir) and os.path.isdir(providers_dir):
            for filename in os.listdir(providers_dir):
                if filename.endswith(('.yaml', '.yml', '.json')):
                    provider_id = os.path.splitext(filename)[0]
                    provider_config = self.load_file(os.path.join(providers_dir, filename))
                    if provider_config:
                        self.settings['llm_providers'][provider_id] = provider_config
                        
        # Override with environment variables
        self._apply_env_overrides()
        
        logger.info(f"Loaded configurations for {len(self.settings['agents'])} agents and "
                   f"{len(self.settings['llm_providers'])} providers")
    
    def _apply_env_overrides(self) -> None:
        """Apply environment variable overrides to the configuration."""
        # Apply global settings
        for key, value in self.env_vars.items():
            parts = key.split('_')
            
            # Handle specific formats like agent_<name>_<setting>
            if len(parts) >= 3 and parts[0] == 'agent':
                agent_id = parts[1]
                setting_key = '_'.join(parts[2:])
                
                if agent_id not in self.settings['agents']:
                    self.settings['agents'][agent_id] = {}
                
                # Navigate to nested settings using dots in the key
                target = self.settings['agents'][agent_id]
                self._set_nested_value(target, setting_key, value)
            
            # Handle provider_<name>_<setting>
            elif len(parts) >= 3 and parts[0] == 'provider':
                provider_id = parts[1]
                setting_key = '_'.join(parts[2:])
                
                if provider_id not in self.settings['llm_providers']:
                    self.settings['llm_providers'][provider_id] = {}
                
                target = self.settings['llm_providers'][provider_id]
                self._set_nested_value(target, setting_key, value)
            
            # Handle global_<setting>
            elif len(parts) >= 2 and parts[0] == 'global':
                setting_key = '_'.join(parts[1:])
                self._set_nested_value(self.settings['global'], setting_key, value)
            
            # Handle other top-level sections
            elif parts[0] in self.settings:
                section = parts[0]
                setting_key = '_'.join(parts[1:])
                self._set_nested_value(self.settings[section], setting_key, value)
    
    def _set_nested_value(self, target: Dict[str, Any], key: str, value: Any) -> None:
        """
        Set a value in a nested dictionary structure.
        
        Args:
            target: Target dictionary
            key: Key with optional dots for nesting
            value: Value to set
        """
        if '.' in key:
            parts = key.split('.', 1)
            current_key, rest = parts
            
            if current_key not in target:
                target[current_key] = {}
            
            if not isinstance(target[current_key], dict):
                target[current_key] = {}
                
            self._set_nested_value(target[current_key], rest, value)
        else:
            target[key] = value
    
    def get_agent_config(self, agent_id: str) -> Dict[str, Any]:
        """
        Get configuration for a specific agent.
        
        Args:
            agent_id: ID of the agent
            
        Returns:
            Agent configuration dictionary
        """
        # Start with global defaults
        config = {}
        
        # Apply global agent defaults
        if 'default' in self.settings['agents']:
            config.update(self.settings['agents']['default'])
        
        # Apply specific agent config
        if agent_id in self.settings['agents']:
            config.update(self.settings['agents'][agent_id])
            
        return config
    
    def get_provider_config(self, provider_id: str) -> Dict[str, Any]:
        """
        Get configuration for a specific LLM provider.
        
        Args:
            provider_id: ID of the provider
            
        Returns:
            Provider configuration dictionary
        """
        # Start with global defaults
        config = {}
        
        # Apply global provider defaults
        if 'default' in self.settings['llm_providers']:
            config.update(self.settings['llm_providers']['default'])
        
        # Apply specific provider config
        if provider_id in self.settings['llm_providers']:
            config.update(self.settings['llm_providers'][provider_id])
            
        return config
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        Get a configuration value by key.
        
        Args:
            key: Configuration key (dot notation for nested keys)
            default: Default value if key not found
            
        Returns:
            Configuration value
        """
        parts = key.split('.')
        
        # Handle special prefixed keys
        if parts[0] == 'agent' and len(parts) >= 3:
            agent_id = parts[1]
            agent_key = '.'.join(parts[2:])
            agent_config = self.get_agent_config(agent_id)
            return self._get_nested_value(agent_config, agent_key, default)
            
        elif parts[0] == 'provider' and len(parts) >= 3:
            provider_id = parts[1]
            provider_key = '.'.join(parts[2:])
            provider_config = self.get_provider_config(provider_id)
            return self._get_nested_value(provider_config, provider_key, default)
        
        # Handle regular keys
        current = self.settings
        for part in parts:
            if isinstance(current, dict) and part in current:
                current = current[part]
            else:
                return default
        
        return current
    
    def _get_nested_value(self, config: Dict[str, Any], key: str, default: Any = None) -> Any:
        """
        Get a nested value from a configuration dictionary.
        
        Args:
            config: Configuration dictionary
            key: Key in dot notation
            default: Default value if key not found
            
        Returns:
            Configuration value
        """
        parts = key.split('.')
        current = config
        
        for part in parts:
            if isinstance(current, dict) and part in current:
                current = current[part]
            else:
                return default
        
        return current
    
    def set(self, key: str, value: Any) -> None:
        """
        Set a configuration value.
        
        Args:
            key: Configuration key (dot notation for nested keys)
            value: Value to set
        """
        parts = key.split('.')
        
        # Handle special prefixed keys
        if parts[0] == 'agent' and len(parts) >= 3:
            agent_id = parts[1]
            agent_key = '.'.join(parts[2:])
            
            if agent_id not in self.settings['agents']:
                self.settings['agents'][agent_id] = {}
                
            self._set_nested_value(self.settings['agents'][agent_id], agent_key, value)
            return
            
        elif parts[0] == 'provider' and len(parts) >= 3:
            provider_id = parts[1]
            provider_key = '.'.join(parts[2:])
            
            if provider_id not in self.settings['llm_providers']:
                self.settings['llm_providers'][provider_id] = {}
                
            self._set_nested_value(self.settings['llm_providers'][provider_id], provider_key, value)
            return
        
        # Handle regular keys
        target = self.settings
        for part in parts[:-1]:
            if part not in target:
                target[part] = {}
            target = target[part]
        
        target[parts[-1]] = value
    
    def validate_required_settings(self, required_settings: List[str]) -> List[str]:
        """
        Validate that required settings are present.
        
        Args:
            required_settings: List of required setting keys
            
        Returns:
            List of missing setting keys
        """
        missing = []
        for key in required_settings:
            if self.get(key) is None:
                missing.append(key)
        
        return missing
    
    def save_config(self, filepath: str) -> None:
        """
        Save current configuration to file.
        
        Args:
            filepath: Path to save the configuration
        """
        filepath = os.path.abspath(filepath)
        file_ext = os.path.splitext(filepath)[1].lower()
        
        try:
            with open(filepath, 'w') as file:
                if file_ext == '.json':
                    json.dump(self.settings, file, indent=2)
                elif file_ext in ('.yaml', '.yml'):
                    yaml.dump(self.settings, file, default_flow_style=False)
                else:
                    logger.error(f"Unsupported config file format: {file_ext}")
                    return
                    
            logger.info(f"Saved configuration to {filepath}")
            
        except Exception as e:
            logger.error(f"Error saving config to {filepath}: {str(e)}")
    
    def validate_agent_config(self, agent_id: str, schema: Dict[str, Any]) -> List[str]:
        """
        Validate agent configuration against a schema.
        
        Args:
            agent_id: ID of the agent to validate
            schema: Validation schema
            
        Returns:
            List of validation errors
        """
        agent_config = self.get_agent_config(agent_id)
        errors = []
        
        # Check required fields
        for field, field_schema in schema.items():
            if field_schema.get('required', False) and field not in agent_config:
                errors.append(f"Missing required field: {field}")
                continue
                
            if field in agent_config:
                value = agent_config[field]
                
                # Type checking
                if 'type' in field_schema:
                    expected_type = field_schema['type']
                    
                    if expected_type == 'string' and not isinstance(value, str):
                        errors.append(f"Field {field} must be a string")
                    elif expected_type == 'number' and not isinstance(value, (int, float)):
                        errors.append(f"Field {field} must be a number")
                    elif expected_type == 'boolean' and not isinstance(value, bool):
                        errors.append(f"Field {field} must be a boolean")
                    elif expected_type == 'array' and not isinstance(value, list):
                        errors.append(f"Field {field} must be an array")
                    elif expected_type == 'object' and not isinstance(value, dict):
                        errors.append(f"Field {field} must be an object")
                
                # Enum validation
                if 'enum' in field_schema and value not in field_schema['enum']:
                    errors.append(f"Field {field} must be one of: {', '.join(field_schema['enum'])}")
                
                # Range validation
                if isinstance(value, (int, float)):
                    if 'minimum' in field_schema and value < field_schema['minimum']:
                        errors.append(f"Field {field} must be at least {field_schema['minimum']}")
                    if 'maximum' in field_schema and value > field_schema['maximum']:
                        errors.append(f"Field {field} must be at most {field_schema['maximum']}")
        
        return errors
    
    def create_default_config(self) -> None:
        """Create a default configuration structure if none exists."""
        # Create config directory if it doesn't exist
        os.makedirs(self.config_dir, exist_ok=True)
        
        # Create subdirectories
        for subdir in ['agents', 'providers', 'tools']:
            os.makedirs(os.path.join(self.config_dir, subdir), exist_ok=True)
        
        # Only create if no config exists yet
        config_file = os.path.join(self.config_dir, 'config.yaml')
        if not os.path.exists(config_file):
            default_config = {
                "global": {
                    "log_level": "info",
                    "default_language": "en",
                    "cache_enabled": True,
                    "cache_ttl": 3600
                },
                "logging": {
                    "file_logging": True,
                    "log_directory": "logs",
                    "max_log_size_mb": 10,
                    "max_log_files": 5
                },
                "security": {
                    "allowed_tools": ["search", "calculator", "weather"],
                    "max_tokens_per_request": 4000,
                    "max_requests_per_minute": 60
                },
                "agents": {
                    "default": {
                        "max_retries": 3,
                        "timeout": 30,
                        "temperature": 0.7
                    }
                },
                "llm_providers": {
                    "default": {
                        "timeout": 60,
                        "retry_on_failure": True,
                        "max_retries": 3
                    }
                }
            }
            
            with open(config_file, 'w') as file:
                yaml.dump(default_config, file, default_flow_style=False)
            
            logger.info(f"Created default configuration at {config_file}")


def load_config(config_dir: Optional[str] = None) -> ConfigManager:
    """
    Load configuration from all available sources.
    
    Args:
        config_dir: Optional configuration directory
        
    Returns:
        Configured ConfigManager instance
    """
    config_manager = ConfigManager(config_dir)
    config_manager.create_default_config()
    config_manager.load_configs()
    config_manager.load_from_env()
    
    return config_manager 