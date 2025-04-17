from src.config import Config
import logging
import os
from datetime import datetime
import time

# Create a single global instance of the Config class to be shared across the application
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
    
    # Add file handler if log_to_file is enabled
    if global_settings.logging.log_to_file:
        # Create log directory if it doesn't exist
        log_dir = global_settings.logging.log_dir
        os.makedirs(log_dir, exist_ok=True)
        
        # Create date-based directory
        today = datetime.now().strftime("%Y-%m-%d")
        date_log_dir = os.path.join(log_dir, today)
        os.makedirs(date_log_dir, exist_ok=True)
        
        # Create global log file
        log_file = os.path.join(log_dir, "global.log")
        
        # Add file handler
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(log_level)
        file_handler.setFormatter(logging.Formatter(log_format))
        
        # Add handler to root logger
        logging.getLogger('').addHandler(file_handler)
        
        # Log initialization message
        logging.info(f"Logging initialized with level {global_settings.logging.level}")

# Initialize logging when this module is imported
setup_logging()

# Export the global_settings instance for importing elsewhere
__all__ = ['global_settings'] 