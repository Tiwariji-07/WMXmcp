"""
Pydantic models for WaveMaker WMX components
"""
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, HttpUrl, Field
from datetime import datetime


class ComponentVersion(BaseModel):
    """Component version information"""
    version: str
    release_date: datetime
    changelog: Optional[str] = None
    compatibility: List[str] = Field(default_factory=list)


class ComponentAuthor(BaseModel):
    """Component author information"""
    name: str
    email: Optional[str] = None
    organization: Optional[str] = None
    profile_url: Optional[HttpUrl] = None


class WMXComponent(BaseModel):
    """WaveMaker WMX Component model"""
    id: str
    name: str
    display_name: str
    description: str
    category: str
    tags: List[str] = Field(default_factory=list)
    
    # Repository information
    git_url: HttpUrl
    git_branch: str = "main"
    git_path: Optional[str] = None  # Path within repo if component is in subfolder
    
    # Metadata
    version: str
    versions: List[ComponentVersion] = Field(default_factory=list)
    author: ComponentAuthor
    license: str = "MIT"
    
    # Images and media
    icon_url: Optional[HttpUrl] = None
    screenshot_urls: List[HttpUrl] = Field(default_factory=list)
    demo_url: Optional[HttpUrl] = None
    
    # Metrics
    downloads: int = 0
    rating: float = 0.0
    reviews_count: int = 0
    
    # Dependencies
    dependencies: List[str] = Field(default_factory=list)
    wavemaker_version: str = ">=11.0.0"
    
    # Timestamps
    created_at: datetime
    updated_at: datetime


class ComponentSearchParams(BaseModel):
    """Search parameters for components"""
    query: Optional[str] = None
    category: Optional[str] = None
    tags: List[str] = Field(default_factory=list)
    author: Optional[str] = None
    min_rating: Optional[float] = None
    limit: int = Field(default=20, ge=1, le=100)
    offset: int = Field(default=0, ge=0)


class ComponentInstallResult(BaseModel):
    """Result of component installation"""
    success: bool
    component_name: str
    install_path: str
    message: str
    files_installed: List[str] = Field(default_factory=list)
    errors: List[str] = Field(default_factory=list)
