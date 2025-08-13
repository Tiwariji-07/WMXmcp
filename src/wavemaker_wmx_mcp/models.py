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


class ComponentValidationResult(BaseModel):
    """Result of component validation for publishing"""
    valid: bool
    component_name: str
    component_path: str
    issues: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    requirements_met: Dict[str, bool] = Field(default_factory=dict)
    suggested_improvements: List[str] = Field(default_factory=list)
    marketplace_ready: bool = False
    structure_valid: bool = True
    metadata: Optional[Dict[str, Any]] = None


class ComponentPublishingData(BaseModel):
    """Data structure for component publishing preparation"""
    success: bool
    component: Optional[Dict[str, Any]] = None
    git_repo: Optional[Dict[str, str]] = None
    files_to_publish: List[Dict[str, Any]] = Field(default_factory=list)
    publishing_steps: List[str] = Field(default_factory=list)
    error: Optional[str] = None
    validation_issues: List[str] = Field(default_factory=list)
    suggestions: List[str] = Field(default_factory=list)


class ComponentPublishResult(BaseModel):
    """Result of component publishing operation"""
    success: bool
    component_id: Optional[str] = None
    component_name: str
    version: Optional[str] = None
    git_repository: Optional[str] = None
    marketplace_url: Optional[str] = None
    message: str
    publishing_details: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    step: Optional[str] = None


class GitRepositoryInfo(BaseModel):
    """Git repository information for publishing"""
    name: str
    description: str
    visibility: str = "public"
    organization: str = "wavemaker-marketplace"
    url: Optional[str] = None  # Make this optional

