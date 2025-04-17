from src.config import Config

# Create a single global instance of the Config class to be shared across the application
global_settings = Config()

# Export the global_settings instance for importing elsewhere
__all__ = ['global_settings'] 