"""
Pydantic models for WaveMaker marketplace artifacts
"""
from typing import List, Optional, Dict, Any, Union
from pydantic import BaseModel, HttpUrl, Field
from datetime import datetime
from enum import Enum

class ArtifactType(str, Enum):
    """Supported artifact types"""
    WMX_COMPONENT = "wmx"
    PREFAB = "prefab"
    CONNECTOR = "connector"
    THEME = "theme"

class ArtifactSearchParams(BaseModel):
    """Search parameters for marketplace artifacts"""
    query: Optional[str] = None
    artifact_type: Optional[ArtifactType] = None
    category: Optional[str] = None
    tags: List[str] = Field(default_factory=list)
    author: Optional[str] = None
    min_rating: Optional[float] = None
    limit: int = Field(default=20, ge=1, le=100)
    offset: int = Field(default=0, ge=0)

class ComponentAuthor(BaseModel):
    """Artifact author information"""
    name: str
    email: Optional[str] = None
    organization: Optional[str] = None
    profile_url: Optional[HttpUrl] = None

class ArtifactVersion(BaseModel):
    """Artifact version information"""
    version: str
    release_date: datetime
    changelog: Optional[str] = None
    compatibility: List[str] = Field(default_factory=list)

class BaseArtifact(BaseModel):
    """Base model for all marketplace artifacts"""
    id: str
    name: str
    display_name: str
    description: str
    artifact_type: ArtifactType
    category: str
    tags: List[str] = Field(default_factory=list)
    
    # Repository information
    git_url: HttpUrl
    git_branch: str = "main"
    git_path: Optional[str] = None
    source_url: Optional[str] = None
    # Metadata
    version: str
    versions: List[ArtifactVersion] = Field(default_factory=list)
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

class WMXComponent(BaseArtifact):
    """WMX Component specific model"""
    artifact_type: ArtifactType = ArtifactType.WMX_COMPONENT
    # WMX-specific fields can be added here if needed

class Prefab(BaseArtifact):
    """Prefab specific model"""
    artifact_type: ArtifactType = ArtifactType.PREFAB
    # Prefab-specific fields
    # widget_dependencies: List[str] = Field(default_factory=list)

class Connector(BaseArtifact):
    """Connector specific model"""
    artifact_type: ArtifactType = ArtifactType.CONNECTOR
    # Connector-specific fields
    # api_endpoints: List[str] = Field(default_factory=list)
    # authentication_type: Optional[str] = None

class Theme(BaseArtifact):
    """Theme specific model"""
    artifact_type: ArtifactType = ArtifactType.THEME
    # Theme-specific fields
    # supported_layouts: List[str] = Field(default_factory=list)
    # color_palette: Dict[str, str] = Field(default_factory=dict)

# Union type for all artifacts
Artifact = Union[WMXComponent, Prefab, Connector, Theme]

class ArtifactInstallResult(BaseModel):
    """Result of artifact installation"""
    success: bool
    artifact_name: str
    artifact_type: ArtifactType
    install_path: str
    message: str
    files_installed: List[str] = Field(default_factory=list)
    project_modifications: List[str] = Field(default_factory=list)  # New field for project changes
    errors: List[str] = Field(default_factory=list)

# class ArtifactInstallPlan(BaseModel):
#     """Installation plan for an artifact"""
#     success: bool
#     artifact: Dict[str, Any]
#     target_path: str
#     files_to_create: List[Dict[str, Any]] = Field(default_factory=list)
#     project_modifications: List[Dict[str, Any]] = Field(default_factory=list)  # Project file changes
#     instructions: str
#     error: Optional[str] = None

# Add this to your existing models.py

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

class GitRepositoryInfo(BaseModel):
    """Git repository information for publishing"""
    name: str
    description: str
    visibility: str = "public"
    organization: str = "wavemaker-marketplace"
    url: Optional[str] = None

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

class ComponentInstallResult(BaseModel):
    """Result of WMX component installation, for legacy compatibility"""
    success: bool
    component_name: str
    install_path: str
    message: str
    files_installed: List[str] = Field(default_factory=list)
    errors: List[str] = Field(default_factory=list)


class InstallAction(BaseModel):
    """Base action for installation"""
    action: str
    path: str
    required: bool = True

class CreateDirectoryAction(InstallAction):
    """Action to create a directory"""
    action: str = "create_directory"

class WriteFileAction(InstallAction):
    """Action to write a file"""
    action: str = "write_file"
    content: str
    encoding: str = "utf-8"  # "utf-8" or "base64"
    is_binary: bool = False
    checksum: str
    size: int
    description: str = ""

class ArtifactInstallPlan(BaseModel):
    """Enhanced installation plan with structured actions"""
    success: bool
    artifact: Dict[str, Any]
    target_path: str
    
    # Legacy support
    files_to_create: List[Dict[str, Any]] = Field(default_factory=list)
    project_modifications: List[Dict[str, Any]] = Field(default_factory=list)
    instructions: str
    
    # New structured actions
    actions: List[Dict[str, Any]] = Field(default_factory=list)
    # verification: Dict[str, Any] = Field(default_factory=dict)
    
    error: Optional[str] = None