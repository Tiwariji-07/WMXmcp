"""
WaveMaker Marketplace API client
"""
import asyncio
import logging
from typing import List, Optional, Dict, Any
import httpx
from models import WMXComponent, ComponentSearchParams
from config import settings

logger = logging.getLogger(__name__)


class WaveMakerAPIClient:
    """Async HTTP client for WaveMaker Marketplace API"""
    
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
                "User-Agent": "WaveMaker-WMX-MCP/1.0.0",
                "Accept": "application/json",
                **({"Authorization": f"Bearer {settings.api_key}"} if settings.api_key else {})
            }
        )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        if self.client:
            await self.client.aclose()
    
    async def search_components(self, params: ComponentSearchParams) -> List[WMXComponent]:
        """
        Search for WMX components in the marketplace
        
        Args:
            params: Search parameters
            
        Returns:
            List of matching components
        """
        try:
            # For now, return mock data - replace with actual API call
            # response = await self.client.get("/components", params=params.dict(exclude_none=True))
            # response.raise_for_status()
            # data = response.json()
            # return [WMXComponent(**item) for item in data["components"]]
            
            return await self._get_mock_components(params)
        
        except httpx.HTTPError as e:
            logger.error(f"HTTP error searching components: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error searching components: {e}")
            raise
    
    async def get_component_details(self, component_id: str) -> Optional[WMXComponent]:
        """
        Get detailed information about a specific component
        
        Args:
            component_id: Unique component identifier
            
        Returns:
            Component details or None if not found
        """
        try:
            # For now, return mock data - replace with actual API call
            # response = await self.client.get(f"/components/{component_id}")
            # if response.status_code == 404:
            #     return None
            # response.raise_for_status()
            # data = response.json()
            # return WMXComponent(**data)
            
            mock_components = await self._get_mock_components(ComponentSearchParams())
            return next((comp for comp in mock_components if comp.id == component_id), None)
        
        except httpx.HTTPError as e:
            logger.error(f"HTTP error getting component {component_id}: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error getting component {component_id}: {e}")
            raise
    
    async def _get_mock_components(self, params: ComponentSearchParams) -> List[WMXComponent]:
        """
        Mock data for development - replace with actual API implementation
        """
        from datetime import datetime
        from models import ComponentAuthor, ComponentVersion
        
        mock_components = [
            WMXComponent(
                id="data-table-advanced",
                name="DataTableAdvanced",
                display_name="Advanced Data Table",
                description="A feature-rich data table component with sorting, filtering, pagination, and export capabilities",
                category="Data Display",
                tags=["table", "data", "grid", "sorting", "filtering"],
                git_url="https://github.com/wavemaker/wmx-data-table-advanced.git",
                git_branch="main",
                version="2.1.0",
                versions=[
                    ComponentVersion(
                        version="2.1.0",
                        release_date=datetime(2024, 8, 1),
                        changelog="Added export functionality and performance improvements",
                        compatibility=["WaveMaker 11.x", "WaveMaker 12.x"]
                    )
                ],
                author=ComponentAuthor(
                    name="WaveMaker Team",
                    email="components@wavemaker.com",
                    organization="WaveMaker Inc."
                ),
                icon_url="https://cdn.wavemaker.com/components/data-table-advanced/icon.png",
                downloads=1250,
                rating=4.8,
                reviews_count=24,
                wavemaker_version=">=11.0.0",
                created_at=datetime(2024, 1, 15),
                updated_at=datetime(2024, 8, 1)
            ),
            WMXComponent(
                id="chart-dashboard",
                name="ChartDashboard",
                display_name="Chart Dashboard Widget",
                description="Interactive dashboard component with multiple chart types and real-time data binding",
                category="Visualization",
                tags=["chart", "dashboard", "visualization", "analytics"],
                git_url="https://github.com/wavemaker/wmx-chart-dashboard.git",
                git_branch="main",
                version="1.5.2",
                versions=[
                    ComponentVersion(
                        version="1.5.2",
                        release_date=datetime(2024, 7, 20),
                        changelog="Bug fixes and responsive design improvements",
                        compatibility=["WaveMaker 11.x", "WaveMaker 12.x"]
                    )
                ],
                author=ComponentAuthor(
                    name="Community Contributor",
                    email="dev@example.com",
                    organization="Independent Developer"
                ),
                icon_url="https://cdn.wavemaker.com/components/chart-dashboard/icon.png",
                downloads=890,
                rating=4.6,
                reviews_count=18,
                dependencies=["chart.js", "moment.js"],
                wavemaker_version=">=11.0.0",
                created_at=datetime(2024, 3, 10),
                updated_at=datetime(2024, 7, 20)
            ),
            WMXComponent(
                id="file-uploader-pro",
                name="FileUploaderPro",
                display_name="Professional File Uploader",
                description="Advanced file upload component with drag-drop, progress tracking, and cloud storage integration",
                category="Input",
                tags=["upload", "file", "drag-drop", "cloud", "storage"],
                git_url="https://github.com/wavemaker/wmx-file-uploader-pro.git",
                git_branch="main",
                version="3.0.1",
                versions=[
                    ComponentVersion(
                        version="3.0.1",
                        release_date=datetime(2024, 8, 5),
                        changelog="Added AWS S3 integration and security enhancements",
                        compatibility=["WaveMaker 12.x"]
                    )
                ],
                author=ComponentAuthor(
                    name="FileUpload Solutions",
                    email="support@fileupload.dev",
                    organization="FileUpload Solutions LLC"
                ),
                icon_url="https://cdn.wavemaker.com/components/file-uploader-pro/icon.png",
                downloads=2100,
                rating=4.9,
                reviews_count=45,
                dependencies=["aws-sdk"],
                wavemaker_version=">=12.0.0",
                created_at=datetime(2023, 11, 5),
                updated_at=datetime(2024, 8, 5)
            ),
            WMXComponent(
                id="RnButton",
                name="RnButton",
                display_name="RnButton",
                description="RnButton",
                category="Input",
                tags=["button", "drag-drop", "form"],
                git_url="https://github.com/Tiwariji-07/RnButton.git",
                git_branch="main",
                version="1.0.0",
                versions=[
                    ComponentVersion(
                        version="1.0.0",
                        release_date=datetime(2024, 8, 5),
                        changelog="Added AWS S3 integration and security enhancements",
                        compatibility=["WaveMaker 12.x"]
                    )
                ],
                author=ComponentAuthor(
                    name="Tiwariji-07",
                    email="support@fileupload.dev",
                    organization="Tiwariji-07"
                ),
                icon_url="https://cdn.wavemaker.com/components/file-uploader-pro/icon.png",
                downloads=2100,
                rating=4.9,
                reviews_count=45,
                dependencies=["aws-sdk"],
                wavemaker_version=">=12.0.0",
                created_at=datetime(2023, 11, 5),
                updated_at=datetime(2024, 8, 5)
            ),
        ]
        
        # Apply basic filtering based on search parameters
        filtered_components = mock_components
        
        if params.query:
            query_lower = params.query.lower()
            filtered_components = [
                comp for comp in filtered_components
                if query_lower in comp.name.lower() 
                or query_lower in comp.description.lower()
                or any(query_lower in tag.lower() for tag in comp.tags)
            ]
        
        if params.category:
            filtered_components = [
                comp for comp in filtered_components
                if comp.category.lower() == params.category.lower()
            ]
        
        if params.tags:
            tag_set = {tag.lower() for tag in params.tags}
            filtered_components = [
                comp for comp in filtered_components
                if tag_set.intersection({tag.lower() for tag in comp.tags})
            ]
        
        # Apply pagination
        start_idx = params.offset
        end_idx = start_idx + params.limit
        return filtered_components[start_idx:end_idx]
