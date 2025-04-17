from src.config import Config
import logging
import os
from datetime import datetime
import time

# Load global configuration
global_settings = Config()

# Set up logging
def setup_logging():
    """Initialize logging configuration based on global settings"""
    log_level = getattr(logging, global_settings.logging.level.upper(), logging.INFO)
    log_format = global_settings.logging.format
    
    # Configure basic settings
    logging.basicConfig(
        level=log_level,
        format=log_format
    )
    
    # Add file handler if file_enabled is enabled
    if global_settings.logging.file_enabled:
        # Get file path
        log_file = global_settings.logging.file_path
        
        # Create directory if it doesn't exist
        log_dir = os.path.dirname(log_file)
        if log_dir:
            os.makedirs(log_dir, exist_ok=True)
        
        # Add file handler
        file_handler = logging.FileHandler(log_file, mode='a')
        file_handler.setLevel(log_level)
        file_handler.setFormatter(logging.Formatter(log_format))
        
        # Add handler to root logger
        logging.getLogger('').addHandler(file_handler)
        
        # Log initialization message
        logging.info(f"Logging initialized with level {global_settings.logging.level}")

# Export the global_settings instance for importing elsewhere
__all__ = ['global_settings', 'setup_logging'] 