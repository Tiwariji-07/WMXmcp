"""
Configuration management for WaveMaker WMX MCP Server
"""
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    """Application settings with environment variable support"""
    
    # API Configuration
    api_base_url: str = "https://api.wavemaker.com/marketplace/v1"
    api_key: Optional[str] = None
    api_timeout: int = 30
    
    # Git Configuration  
    git_clone_timeout: int = 300
    git_depth: int = 1
    
    # Component Installation
    component_base_path: str = "src/main/webapp/components"
    max_component_size_mb: int = 100
    
    # Logging
    log_level: str = "INFO"
    log_format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    
    # Use the new ConfigDict approach
    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="WAVEMAKER_"
    )



# Global settings instance
settings = Settings()
