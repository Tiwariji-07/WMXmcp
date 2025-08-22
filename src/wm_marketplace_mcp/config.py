"""
Configuration management for WaveMaker WMX MCP Server
"""
import os
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings with environment variable support"""
    
    # API Configuration - Updated for real WaveMaker API
    api_base_url: str = "https://dev-marketplaceservices.onwavemaker.com"
    api_key: Optional[str] = None
    api_timeout: int = 30
    
    # Git Configuration
    git_clone_timeout: int = 300
    git_depth: int = 1  # Shallow clone for performance
    
    # Artifact Installation Paths - Centralized configuration
    wmx_component_base_path: str = "src/main/webapp/components"
    prefab_base_path: str = "src/main/webapp/WEB-INF/prefabs" 
    connector_base_path: str = "src/main/webapp/WEB-INF/connectors"
    theme_base_path: str = "src/main/webapp/themes"
    
    # Legacy - keeping for backward compatibility
    component_base_path: str = "src/main/webapp/components"  
    
    # File size limits
    max_component_size_mb: int = 100
    
    # Publishing Configuration
    git_organization: str = "wavemaker-marketplace"
    git_token: Optional[str] = None
    git_username: Optional[str] = None
    
    # Logging
    log_level: str = "INFO"
    log_format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

    # Build Configuration
    auto_build_connectors: bool = True  # Enable automatic connector building
    build_timeout_seconds: int = 300   # 5 minute build timeout
    require_build_tools: bool = True   # Require Maven/Java in MCP environment
    
    # Use the new ConfigDict approach
    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="WAVEMAKER_"
    )


# Global settings instance
settings = Settings()
