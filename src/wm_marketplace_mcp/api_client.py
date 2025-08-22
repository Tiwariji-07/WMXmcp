
"""
WaveMaker Marketplace API client for all artifact types
"""
import asyncio
import logging
from typing import List, Optional, Dict, Any
import httpx
from models import (
    ArtifactSearchParams, ArtifactType, BaseArtifact, 
    WMXComponent, Prefab, Connector, Theme,
    ComponentAuthor, ArtifactVersion
)
from config import settings
from datetime import datetime

logger = logging.getLogger(__name__)

class WaveMakerAPIClient:
    """Unified API client for all marketplace artifacts"""
    
    # Artifact type ID mapping
    ARTIFACT_TYPE_IDS = {
        ArtifactType.WMX_COMPONENT: "26",
        ArtifactType.PREFAB: "25",  # Example IDs - adjust based on actual API
        ArtifactType.CONNECTOR: "27",
        ArtifactType.THEME: "28"
    }
    
    def __init__(self):
        self.base_url = settings.api_base_url
        self.timeout = settings.api_timeout
        self.client: Optional[httpx.AsyncClient] = None
    
    async def __aenter__(self):
        """Async context manager entry"""
        self.client = httpx.AsyncClient(
            base_url=self.base_url,
            timeout=self.timeout,
            headers={
                "User-Agent": "WaveMaker-Marketplace-MCP/1.0.0",
                "Accept": "application/json",
                **({"Authorization": f"Bearer {settings.api_key}"} if settings.api_key else {})
            }
        )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        if self.client:
            await self.client.aclose()
    
    async def search_artifacts(self, params: ArtifactSearchParams) -> List[BaseArtifact]:
        """
        Search for artifacts in the marketplace
        """
        try:
            # Build query parameters
            query_params = {}
            
            if params.artifact_type:
                query_params["artifactTypeIds"] = self.ARTIFACT_TYPE_IDS[params.artifact_type]
            else:
                # Search all types
                query_params["artifactTypeIds"] = ",".join(self.ARTIFACT_TYPE_IDS.values())
            
            if params.query:
                query_params["name"] = params.query
            
            if params.limit:
                query_params["size"] = min(params.limit, 100)
            
            if params.offset:
                query_params["page"] = params.offset // params.limit if params.limit > 0 else 0
            
            logger.info(f"Searching artifacts with params: {query_params}")
            
            # For now, return mock data
            return await self._get_mock_artifacts(params)
            
        except Exception as e:
            logger.error(f"Error searching artifacts: {e}")
            return await self._get_mock_artifacts(params)
    
    async def get_artifact_details(self, artifact_id: str) -> Optional[BaseArtifact]:
        """Get detailed information about a specific artifact"""
        try:
            # For now, return mock data
            mock_artifacts = await self._get_mock_artifacts(ArtifactSearchParams())
            return next((artifact for artifact in mock_artifacts if artifact.id == artifact_id), None)
            
        except Exception as e:
            logger.error(f"Error getting artifact details for {artifact_id}: {e}")
            return None
    
    async def _get_mock_artifacts(self, params: ArtifactSearchParams) -> List[BaseArtifact]:
        """Mock data for all artifact types"""
        from datetime import datetime
        
        mock_artifacts = [
            # WMX Components
            WMXComponent(
                id="wmx-data-table",
                name="DataTable",
                display_name="Advanced Data Table",
                description="Feature-rich data table with sorting, filtering, and pagination",
                category="Data Display",
                tags=["table", "data", "grid"],
                git_url="https://github.com/wavemaker/wmx-data-table.git",
                version="2.1.0",
                author=ComponentAuthor(name="WaveMaker Team", organization="WaveMaker Inc."),
                downloads=1250,
                rating=4.8,
                created_at=datetime(2024, 1, 15),
                updated_at=datetime(2024, 8, 1)
            ),
            WMXComponent(
                id="wmx-button",
                name="WMXButton",
                display_name="WMXButton",
                description="Feature-rich data table with sorting, filtering, and pagination",
                category="Data Display",
                tags=["table", "data", "grid"],
                git_url="https://github.com/Tiwariji-07/rnbutton",
                version="2.1.0",
                author=ComponentAuthor(name="WaveMaker Team", organization="WaveMaker Inc."),
                downloads=1250,
                rating=4.8,
                created_at=datetime(2024, 1, 15),
                updated_at=datetime(2024, 8, 1)
            ),
            
            # Prefabs
            Prefab(
                id="prefab-login-form",
                name="LoginForm",
                display_name="Login Form Prefab",
                description="Ready-to-use login form with validation and authentication",
                category="Authentication",
                tags=["login", "form", "auth"],
                git_url="https://github.com/wavemaker/prefab-login-form.git",
                version="1.0.0",
                author=ComponentAuthor(name="WaveMaker Team", organization="WaveMaker Inc."),
                # widget_dependencies=["wm-form", "wm-button", "wm-text"],
                downloads=850,
                rating=4.6,
                created_at=datetime(2024, 2, 10),
                updated_at=datetime(2024, 7, 15)
            ),
            
            # Connectors
            Connector(
                id="google-cloud-file-storage-connector",
                name="GoogleCloudFileStorageConnector",
                display_name="Google Cloud File Storage Connector",
                description="Connect to Google Cloud File Storage APIs for file storage processing",
                category="File Storage",
                tags=["google", "cloud", "file", "storage"],
                git_url="https://github.com/wm-marketplace/google-cloud-file-storage-connector",
                source_url="",
                version="1.2.0",
                author=ComponentAuthor(name="WaveMaker Team", organization="WaveMaker Inc."),
                # api_endpoints=["/charge", "/refund", "/customer"],
                # authentication_type="API_KEY",
                downloads=420,
                rating=4.7,
                created_at=datetime(2024, 3, 5),
                updated_at=datetime(2024, 8, 10)
            ),
            Connector(
                id="rabbitmq-connector",
                name="RabbitMQConnector",
                display_name="RabbitMQ Connector",
                description="Connect to RabbitMQ APIs for message processing",
                category="Message Processing",
                tags=["rabbitmq", "connector", "message", "processing"],
                git_url="https://github.com/wm-marketplace/rabbitmq-connector",
                source_url="",
                version="1.2.0",
                author=ComponentAuthor(name="WaveMaker Team", organization="WaveMaker Inc."),
                # api_endpoints=["/charge", "/refund", "/customer"],
                # authentication_type="API_KEY",
                downloads=420,
                rating=4.7,
                created_at=datetime(2024, 3, 5),
                updated_at=datetime(2024, 8, 10)
            ),
            Connector(
                id="excel-connector",
                name="ExcelConnector",
                display_name="Excel Connector",
                description="Connect to Excel APIs for data processing",
                category="Data Processing",
                tags=["excel", "connector", "data", "processing"],
                git_url="https://github.com/wm-marketplace/excel-connector",
                source_url="https://github.com/wm-marketplace/excel-connector/releases/download/1.0.0/excel-connector_2.0.zip",
                version="1.2.0",
                author=ComponentAuthor(name="WaveMaker Team", organization="WaveMaker Inc."),
                # api_endpoints=["/charge", "/refund", "/customer"],
                # authentication_type="API_KEY",
                downloads=420,
                rating=4.7,
                created_at=datetime(2024, 3, 5),
                updated_at=datetime(2024, 8, 10)
            ),
            
            # Themes
            Theme(
                id="theme-material-dark",
                name="MaterialDark",
                display_name="Material Dark Theme",
                description="Dark theme based on Material Design principles",
                category="Theme",
                tags=["dark", "material", "modern"],
                git_url="https://github.com/wavemaker/theme-material-dark.git",
                version="1.0.5",
                author=ComponentAuthor(name="WaveMaker Team", organization="WaveMaker Inc."),
                # supported_layouts=["desktop", "mobile", "tablet"],
                # color_palette={"primary": "#1976d2", "accent": "#ff4081", "background": "#303030"},
                downloads=2100,
                rating=4.9,
                created_at=datetime(2024, 1, 20),
                updated_at=datetime(2024, 7, 25)
            )
        ]
        
        # Apply filtering
        filtered_artifacts = mock_artifacts
        
        if params.artifact_type:
            filtered_artifacts = [
                artifact for artifact in filtered_artifacts
                if artifact.artifact_type == params.artifact_type
            ]
        
        if params.query:
            query_lower = params.query.lower()
            filtered_artifacts = [
                artifact for artifact in filtered_artifacts
                if query_lower in artifact.name.lower() 
                or query_lower in artifact.description.lower()
                or any(query_lower in tag.lower() for tag in artifact.tags)
            ]
        
        if params.category:
            filtered_artifacts = [
                artifact for artifact in filtered_artifacts
                if artifact.category.lower() == params.category.lower()
            ]
        
        # Apply pagination
        start_idx = params.offset
        end_idx = start_idx + params.limit
        return filtered_artifacts[start_idx:end_idx]
