"""
Component publishing utilities for marketplace
"""
import json
import logging
import tempfile
import time
import os
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime

from models import (
    ComponentPublishingData, 
    ComponentPublishResult, 
    WMXComponent,
    GitRepositoryInfo
)
from component_validator import ComponentValidator
from git_manager import GitManager
from api_client import WaveMakerAPIClient
from config import settings

logger = logging.getLogger(__name__)

class ComponentPublisher:
    """Handles publishing of WMX components to marketplace"""
    
    def __init__(self):
        self.validator = ComponentValidator()
        self.git_manager = GitManager()
    
    async def prepare_component_for_publishing(
    self,
    component_path: str,
    git_repo_name: Optional[str] = None,
    marketplace_category: Optional[str] = None,
    tags: Optional[List[str]] = None,
    author_info: Optional[Dict[str, str]] = None
) -> ComponentPublishingData:
        """
        Prepare a local WMX component for marketplace publishing
        """
        try:
            # First validate the component
            validation_result = await self.validator.validate_component(
                component_path, 
                strict_validation=True
            )
            
            if not validation_result.marketplace_ready:
                return ComponentPublishingData(
                    success=False,
                    error="Component is not ready for publishing",
                    validation_issues=validation_result.issues,
                    suggestions=validation_result.suggested_improvements
                )
            
            component_dir = Path(component_path)
            component_metadata = validation_result.metadata or {}
            component_name = component_metadata.get("name", component_dir.name)
            
            # Try to get Git URL from component metadata
            git_url = None
            if "repository" in component_metadata and isinstance(component_metadata["repository"], dict):
                git_url = component_metadata["repository"].get("url")
            elif "git_repo" in component_metadata and isinstance(component_metadata["git_repo"], dict):
                git_url = component_metadata["git_repo"].get("url")
            
            # If no Git URL found, create a default one
            if not git_url:
                git_url = f"https://github.com/wavemaker-marketplace/{git_repo_name or f'wmx-{component_name.lower().replace(' ', '-')}'}"
            
            # Prepare publishing data
            git_repo_info = GitRepositoryInfo(
                name=git_repo_name or f"wmx-{component_name.lower().replace(' ', '-')}",
                description=f"WMX Component: {component_metadata.get('description', component_name)}",
                visibility="public",
                url=git_url  # ADD THIS LINE
            )
            
            publishing_data = ComponentPublishingData(
                success=True,
                component={
                    "name": component_name,
                    "display_name": component_metadata.get("displayName", component_name),
                    "description": component_metadata.get("description", ""),
                    "version": component_metadata.get("version", "1.0.0"),
                    "category": marketplace_category or component_metadata.get("category", "Custom"),
                    "tags": tags or component_metadata.get("tags", []),
                    "author": author_info or {
                        "name": component_metadata.get("author", "Unknown"),
                        "email": "",
                        "organization": ""
                    },
                    "license": component_metadata.get("license", "MIT"),
                    "wavemaker_version": component_metadata.get("wavemakerVersion", ">=11.0.0"),
                    "dependencies": component_metadata.get("dependencies", [])
                },
                git_repo=git_repo_info.dict(),
                publishing_steps=[
                    "1. Validate component structure and metadata",
                    "2. Prepare component files for publishing",
                    "3. Create Git repository in marketplace organization", 
                    "4. Upload component files to repository",
                    "5. Register component in marketplace database",
                    "6. Generate component documentation",
                    "7. Publish component to marketplace"
                ]
            )
            
            # Scan all files to be published
            publishing_data.files_to_publish = await self._scan_component_files(component_dir)
            
            return publishing_data
            
        except Exception as e:
            logger.error(f"Error preparing component for publishing: {e}")
            return ComponentPublishingData(
                success=False,
                error=str(e)
            )

    async def simulate_component_publishing(
    self,
    component_path: str,
    marketplace_config: Dict[str, str],
    git_config: Optional[Dict[str, str]] = None,
    **publish_options
) -> ComponentPublishResult:
        """
        Simulate component publishing (dry run) without actually publishing
        """
        try:
            # Prepare component
            prep_result = await self.prepare_component_for_publishing(
                component_path,
                **publish_options
            )
            
            if not prep_result.success:
                return ComponentPublishResult(
                    success=False,
                    component_name="Unknown",
                    error=prep_result.error,
                    message=f"Preparation failed: {prep_result.error}",  # ADD THIS LINE
                    step="preparation"
                )
            
            component_data = prep_result.component
            
            # Simulate the publishing process
            simulated_component_id = f"comp_{component_data['name'].lower().replace(' ', '_')}_{int(time.time())}"
            simulated_repo_url = f"https://github.com/wavemaker-marketplace/{prep_result.git_repo['name']}"
            simulated_marketplace_url = f"{marketplace_config.get('base_url', 'https://marketplace.wavemaker.com')}/components/{simulated_component_id}"
            
            return ComponentPublishResult(
                success=True,
                component_id=simulated_component_id,
                component_name=component_data["name"],
                version=component_data["version"],
                git_repository=simulated_repo_url,
                marketplace_url=simulated_marketplace_url,
                message=f"[DRY RUN] Component '{component_data['name']}' would be published successfully!",
                publishing_details={
                    "repository_would_be_created": simulated_repo_url,
                    "files_to_upload": len(prep_result.files_to_publish),
                    "marketplace_id_would_be": simulated_component_id,
                    "dry_run": True
                }
            )
            
        except Exception as e:
            logger.error(f"Error simulating component publishing: {e}")
            return ComponentPublishResult(
                success=False,
                component_name="Unknown",
                error=str(e),
                message=f"Simulation failed: {str(e)}",  # ADD THIS LINE
                step="simulation"
            )

    async def _scan_component_files(self, component_dir: Path) -> List[Dict[str, Any]]:
        """Scan component directory and return file information"""
        files_to_publish = []
        
        for root, dirs, files in os.walk(component_dir):
            # Skip hidden directories and version control
            dirs[:] = [d for d in dirs if not d.startswith('.') and d != 'node_modules']
            
            for file in files:
                if not file.startswith('.') and not file.endswith('.tmp'):
                    file_path = Path(root) / file
                    relative_path = file_path.relative_to(component_dir)
                    
                    files_to_publish.append({
                        "path": str(relative_path),
                        "size": file_path.stat().st_size,
                        "type": self._get_file_type(file_path),
                        "description": f"Component file: {relative_path}"
                    })
        
        return files_to_publish
    
    def _get_file_type(self, file_path: Path) -> str:
        """Determine file type based on extension"""
        suffix = file_path.suffix.lower()
        type_mapping = {
            '.ts': 'typescript',
            '.js': 'javascript',
            '.json': 'json',
            '.html': 'html',
            '.css': 'css',
            '.scss': 'scss',
            '.md': 'markdown',
            '.png': 'image',
            '.jpg': 'image',
            '.jpeg': 'image',
            '.svg': 'svg',
            '.xml': 'xml',
            '.txt': 'text'
        }
        return type_mapping.get(suffix, 'unknown')

    async def register_component_in_marketplace(
        self,
        component_data: Dict[str, Any],
        marketplace_config: Dict[str, str]
    ) -> Dict[str, Any]:
        """
        Register component with marketplace API (mock implementation)
        Replace with actual API calls when marketplace API is available
        """
        try:
            # Mock implementation - replace with actual API calls
            api_payload = {
                "name": component_data["name"],
                "display_name": component_data["display_name"],
                "description": component_data["description"],
                "version": component_data["version"],
                "category": component_data["category"],
                "tags": component_data["tags"],
                "author": component_data["author"],
                "git_url": component_data.get("git_url"),
                "license": component_data["license"],
                "wavemaker_version": component_data["wavemaker_version"],
                "dependencies": component_data["dependencies"]
            }
            
            logger.info(f"Would register component with marketplace: {api_payload}")
            
            # Simulate API call
            component_id = f"comp_{component_data['name'].lower().replace(' ', '_')}_{int(time.time())}"
            marketplace_url = f"{marketplace_config.get('base_url', 'https://marketplace.wavemaker.com')}/components/{component_id}"
            
            return {
                "success": True,
                "component_id": component_id,
                "marketplace_url": marketplace_url
            }
            
        except Exception as e:
            logger.error(f"Error registering component in marketplace: {e}")
            return {
                "success": False,
                "error": str(e)
            }
