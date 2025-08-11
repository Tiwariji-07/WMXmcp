"""
WaveMaker WMX Component MCP Server
"""
import asyncio
import logging
from typing import List, Optional, Any, Dict
from pathlib import Path
import json

from fastmcp import FastMCP  # Use the NEW fastmcp library

from api_client import WaveMakerAPIClient  
from git_manager import GitManager
from models import ComponentSearchParams, WMXComponent, ComponentInstallResult
from config import settings

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.log_level.upper()),
    format=settings.log_format
)
logger = logging.getLogger(__name__)

# Initialize MCP server
mcp = FastMCP(
    name="WaveMaker WMX Components",
    dependencies=["httpx", "gitpython", "pydantic", "aiofiles"]
)

@mcp.tool()
async def search_wmx_components(
    query: Optional[str] = None,
    category: Optional[str] = None, 
    tags: Optional[List[str]] = None,
    limit: int = 10
) -> Dict[str, Any]:
    """
    Search for WMX components in the WaveMaker marketplace
    
    Args:
        query: Search query string (component name, description keywords)
        category: Component category filter (Data Display, Visualization, Input, etc.)
        tags: List of tags to filter by
        limit: Maximum number of results to return (1-50)
    
    Returns:
        Dictionary containing search results and metadata
    """
    try:
        logger.info(f"Searching components: query='{query}', category='{category}', tags={tags}")
        
        # Validate inputs
        if limit > 50:
            limit = 50
        elif limit < 1:
            limit = 1
        
        search_params = ComponentSearchParams(
            query=query,
            category=category, 
            tags=tags or [],
            limit=limit
        )
        
        async with WaveMakerAPIClient() as client:
            components = await client.search_components(search_params)
        
        result = {
            "total_found": len(components),
            "components": [
                {
                    "id": comp.id,
                    "name": comp.name,
                    "display_name": comp.display_name,
                    "description": comp.description,
                    "category": comp.category,
                    "tags": comp.tags,
                    "version": comp.version,
                    "author": comp.author.name,
                    "rating": comp.rating,
                    "downloads": comp.downloads,
                    "git_url": str(comp.git_url)
                }
                for comp in components
            ],
            "search_params": {
                "query": query,
                "category": category,
                "tags": tags,
                "limit": limit
            }
        }
        
        logger.info(f"Found {len(components)} components matching search criteria")
        return result
        
    except Exception as e:
        logger.error(f"Error searching components: {e}")
        return {
            "error": str(e),
            "total_found": 0,
            "components": [],
            "search_params": {"query": query, "category": category, "tags": tags, "limit": limit}
        }

@mcp.tool()
async def get_component_details(component_id: str) -> Dict[str, Any]:
    """
    Get detailed information about a specific WMX component
    
    Args:
        component_id: Unique identifier of the component
        
    Returns:
        Dictionary containing detailed component information
    """
    try:
        logger.info(f"Getting component details for: {component_id}")
        
        async with WaveMakerAPIClient() as client:
            component = await client.get_component_details(component_id)
        
        if not component:
            return {
                "error": f"Component with ID '{component_id}' not found",
                "component": None
            }
        
        result = {
            "component": {
                "id": component.id,
                "name": component.name,
                "display_name": component.display_name,
                "description": component.description,
                "category": component.category,
                "tags": component.tags,
                "version": component.version,
                "versions": [
                    {
                        "version": v.version,
                        "release_date": v.release_date.isoformat(),
                        "changelog": v.changelog,
                        "compatibility": v.compatibility
                    }
                    for v in component.versions
                ],
                "author": {
                    "name": component.author.name,
                    "email": component.author.email,
                    "organization": component.author.organization
                },
                "git_url": str(component.git_url),
                "git_branch": component.git_branch,
                "license": component.license,
                "rating": component.rating,
                "downloads": component.downloads,
                "reviews_count": component.reviews_count,
                "dependencies": component.dependencies,
                "wavemaker_version": component.wavemaker_version,
                "icon_url": str(component.icon_url) if component.icon_url else None,
                "demo_url": str(component.demo_url) if component.demo_url else None,
                "created_at": component.created_at.isoformat(),
                "updated_at": component.updated_at.isoformat()
            }
        }
        
        logger.info(f"Retrieved details for component: {component.name}")
        return result
        
    except Exception as e:
        logger.error(f"Error getting component details for {component_id}: {e}")
        return {
            "error": str(e),
            "component": None
        }

@mcp.tool()
async def install_wmx_component(
    component_id: str,
    target_path: Optional[str] = None,
    force_overwrite: bool = False
) -> Dict[str, Any]:
    """
    Install a WMX component from the marketplace to the WaveMaker project
    
    Args:
        component_id: Unique identifier of the component to install
        target_path: Custom installation path (defaults to src/main/webapp/components)
        force_overwrite: Whether to overwrite existing component installation
        
    Returns:
        Dictionary containing installation result and details
    """
    try:
        logger.info(f"Installing component: {component_id}")
        
        # Get component details
        async with WaveMakerAPIClient() as client:
            component = await client.get_component_details(component_id)
        
        if not component:
            return {
                "success": False,
                "error": f"Component with ID '{component_id}' not found",
                "component_name": component_id,
                "install_path": None
            }
        
        # Determine installation path
        install_base_path = target_path or settings.component_base_path
        component_install_path = Path(install_base_path) / component.name
        
        # Check if component already exists
        if component_install_path.exists() and not force_overwrite:
            return {
                "success": False,
                "error": f"Component '{component.name}' already exists at {component_install_path}. Use force_overwrite=true to replace.",
                "component_name": component.name,
                "install_path": str(component_install_path)
            }
        
        # Remove existing installation if force overwrite
        if force_overwrite and component_install_path.exists():
            import shutil
            shutil.rmtree(component_install_path)
            logger.info(f"Removed existing component installation: {component_install_path}")
        
        # Install component using git_manager (you'll need to create this)
        from git_manager import GitManager
        git_manager = GitManager()
        result = await git_manager.install_component(component, install_base_path)
        
        # Convert to dictionary for JSON serialization
        result_dict = {
            "success": result.success,
            "component_name": result.component_name,
            "install_path": result.install_path,
            "message": result.message,
            "files_installed": result.files_installed,
            "errors": result.errors,
            "component_details": {
                "id": component.id,
                "version": component.version,
                "git_url": str(component.git_url),
                "author": component.author.name
            }
        }
        
        if result.success:
            logger.info(f"Successfully installed component {component.name}")
        else:
            logger.error(f"Failed to install component {component.name}: {result.message}")
        
        return result_dict
        
    except Exception as e:
        logger.error(f"Error installing component {component_id}: {e}")
        return {
            "success": False,
            "error": str(e),
            "component_name": component_id,
            "install_path": None
        }

@mcp.tool()
async def list_installed_components(
    base_path: Optional[str] = None
) -> Dict[str, Any]:
    """
    List all installed WMX components in the project
    
    Args:
        base_path: Base path where components are installed (defaults to src/main/webapp/components)
        
    Returns:
        Dictionary containing list of installed components
    """
    try:
        components_path = Path(base_path or settings.component_base_path)
        
        if not components_path.exists():
            return {
                "installed_components": [],
                "total_count": 0,
                "components_path": str(components_path),
                "message": f"Components directory not found: {components_path}"
            }
        
        installed_components = []
        
        for component_dir in components_path.iterdir():
            if component_dir.is_dir() and not component_dir.name.startswith('.'):
                metadata_file = component_dir / ".wmx-component-metadata.json"
                
                component_info = {
                    "name": component_dir.name,
                    "path": str(component_dir),
                    "has_metadata": metadata_file.exists()
                }
                
                # Load metadata if available
                if metadata_file.exists():
                    try:
                        with open(metadata_file, 'r') as f:
                            metadata = json.load(f)
                            component_info.update({
                                "id": metadata.get("id"),
                                "version": metadata.get("version"),
                                "description": metadata.get("description"),
                                "author": metadata.get("author", {}).get("name"),
                                "installed_at": metadata.get("installed_at"),
                                "source_url": metadata.get("source_url")
                            })
                    except Exception as e:
                        logger.warning(f"Failed to read metadata for {component_dir.name}: {e}")
                
                installed_components.append(component_info)
        
        return {
            "installed_components": installed_components,
            "total_count": len(installed_components),
            "components_path": str(components_path)
        }
        
    except Exception as e:
        logger.error(f"Error listing installed components: {e}")
        return {
            "error": str(e),
            "installed_components": [],
            "total_count": 0
        }

# Use the simple main function like your working example
if __name__ == "__main__":
    mcp.run()
