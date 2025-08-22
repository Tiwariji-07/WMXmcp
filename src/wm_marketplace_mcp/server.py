"""
WaveMaker Marketplace MCP Server - Unified for all artifact types
"""
import asyncio
import logging
from typing import List, Optional, Any, Dict
from pathlib import Path
import json
import requests
import zipfile
import base64
import os

from typing import Annotated,Literal
# from enum import Literal
from pydantic import Field
from fastmcp import FastMCP
from api_client import WaveMakerAPIClient
from git_manager import GitManager
from models import ArtifactSearchParams, ArtifactType, BaseArtifact
from config import settings
from artifact_installer import ArtifactInstaller  # New unified installer

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.log_level.upper()),
    format=settings.log_format
)
logger = logging.getLogger(__name__)

# Initialize MCP server
mcp = FastMCP(
    name="WaveMaker Marketplace",
    dependencies=["httpx", "gitpython", "pydantic", "aiofiles"]
)

@mcp.tool(
    description="Search for artifacts in the WaveMaker marketplace. Use this to find WMX components, prefabs, connectors, and themes.",
)
async def search_marketplace_artifacts(
    query: Annotated[
        Optional[str], 
        Field(description="Search query string to find artifacts by name or description")
    ] = None,
    artifact_type: Annotated[
        Optional[Literal["wmx", "prefab", "connector", "theme"]], 
        Field(description="Type of artifact to filter by")
    ] = None,
    category: Annotated[
        Optional[str], 
        Field(description="Category filter to narrow down results")
    ] = None,
    tags: Annotated[
        Optional[List[str]], 
        Field(description="List of tags to filter artifacts")
    ] = None,
    limit: Annotated[
        int, 
        Field(description="Maximum number of results to return", ge=1, le=50)
    ] = 10
    ) -> Dict[str, Any]:
    """
    Search for artifacts in the WaveMaker marketplace
    
    Args:
        query: Search query string
        artifact_type: Type of artifact (wmx, prefab, connector, theme)
        category: Category filter
        tags: List of tags to filter by
        limit: Maximum number of results (1-50)
    
    Returns:
        Dictionary containing search results and metadata
    """
    try:
        logger.info(f"Searching artifacts: query='{query}', type='{artifact_type}', category='{category}'")
        
        # Validate and convert artifact type
        artifact_type_enum = None
        if artifact_type:
            try:
                artifact_type_enum = ArtifactType(artifact_type)
            except ValueError:
                return {
                    "error": f"Invalid artifact type: {artifact_type}. Valid types: {[t.value for t in ArtifactType]}",
                    "total_found": 0,
                    "artifacts": []
                }
        
        # Validate inputs
        if limit > 50:
            limit = 50
        elif limit < 1:
            limit = 1
        
        search_params = ArtifactSearchParams(
            query=query,
            artifact_type=artifact_type_enum,
            category=category,
            tags=tags or [],
            limit=limit
        )
        
        async with WaveMakerAPIClient() as client:
            artifacts = await client.search_artifacts(search_params)
        
        result = {
            "total_found": len(artifacts),
            "artifacts": [
                {
                    "id": artifact.id,
                    "name": artifact.name,
                    "display_name": artifact.display_name,
                    "description": artifact.description,
                    "artifact_type": artifact.artifact_type.value,
                    "category": artifact.category,
                    "tags": artifact.tags,
                    "version": artifact.version,
                    "author": artifact.author.name,
                    "rating": artifact.rating,
                    "downloads": artifact.downloads,
                    "git_url": str(artifact.git_url)
                }
                for artifact in artifacts
            ],
            "search_params": {
                "query": query,
                "artifact_type": artifact_type,
                "category": category,
                "tags": tags,
                "limit": limit
            }
        }
        
        logger.info(f"Found {len(artifacts)} artifacts matching search criteria")
        return result
        
    except Exception as e:
        logger.error(f"Error searching artifacts: {e}")
        return {
            "error": str(e),
            "total_found": 0,
            "artifacts": [],
            "search_params": {"query": query, "artifact_type": artifact_type, "category": category, "tags": tags, "limit": limit}
        }

@mcp.tool(
    description="Get detailed information about a specific marketplace artifact. Use this to see full details, versions, dependencies, and metadata before installation.",
)
async def get_artifact_details(
    artifact_id: Annotated[
        str, 
        Field(description="Unique identifier of the artifact to retrieve details for")
    ]
    ) -> Dict[str, Any]:
    """
    Get detailed information about a specific marketplace artifact
    
    Args:
        artifact_id: Unique identifier of the artifact
        
    Returns:
        Dictionary containing detailed artifact information
    """
    try:
        logger.info(f"Getting artifact details for: {artifact_id}")
        
        async with WaveMakerAPIClient() as client:
            artifact = await client.get_artifact_details(artifact_id)
        
        if not artifact:
            return {
                "error": f"Artifact with ID '{artifact_id}' not found",
                "artifact": None
            }
        
        result = {
            "artifact": {
                "id": artifact.id,
                "name": artifact.name,
                "display_name": artifact.display_name,
                "description": artifact.description,
                "artifact_type": artifact.artifact_type.value,
                "category": artifact.category,
                "tags": artifact.tags,
                "version": artifact.version,
                "versions": [
                    {
                        "version": v.version,
                        "release_date": v.release_date.isoformat(),
                        "changelog": v.changelog,
                        "compatibility": v.compatibility
                    }
                    for v in artifact.versions
                ],
                "author": {
                    "name": artifact.author.name,
                    "email": artifact.author.email,
                    "organization": artifact.author.organization
                },
                "git_url": str(artifact.git_url),
                "git_branch": artifact.git_branch,
                "license": artifact.license,
                "rating": artifact.rating,
                "downloads": artifact.downloads,
                "reviews_count": artifact.reviews_count,
                "dependencies": artifact.dependencies,
                "wavemaker_version": artifact.wavemaker_version,
                "icon_url": str(artifact.icon_url) if artifact.icon_url else None,
                "demo_url": str(artifact.demo_url) if artifact.demo_url else None,
                "created_at": artifact.created_at.isoformat(),
                "updated_at": artifact.updated_at.isoformat()
            }
        }
        
        # Add artifact-type specific fields
        if hasattr(artifact, 'widget_dependencies'):
            result["artifact"]["widget_dependencies"] = artifact.widget_dependencies
        if hasattr(artifact, 'api_endpoints'):
            result["artifact"]["api_endpoints"] = artifact.api_endpoints
        if hasattr(artifact, 'color_palette'):
            result["artifact"]["color_palette"] = artifact.color_palette
        
        logger.info(f"Retrieved details for artifact: {artifact.name}")
        return result
        
    except Exception as e:
        logger.error(f"Error getting artifact details for {artifact_id}: {e}")
        return {
            "error": str(e),
            "artifact": None
        }

@mcp.tool(description=""""Prepare artifact installation plan. After getting this plan:
    
    1. If the response contains 'actions' array with 'download_and_extract' action:
       → Perform the download and extraction as per the instructions
    2. If the response contains 'files_to_create' array:
       → Create each file manually using the provided content
    
    
    DO NOT manually download/extract if structured actions are provided.""")
async def execute_artifact_installation(
    artifact_id: Annotated[
        str, 
        Field(description="Unique identifier of the artifact to install")
    ],
    project_path: Annotated[
        str, 
        Field(description="Path to the WaveMaker project where the artifact should be installed. If not provided, uses current working directory.")
    ] = None
    ) -> Dict[str, Any]:
    """
    Prepare artifact installation by analyzing files and project modifications needed
    
    Args:
        artifact_id: Unique identifier of the artifact to install
        project_path: Project Path, it is path of the project where artifact is to be installed
        
    Returns:
        Dictionary containing installation plan with files and project modifications
    """
    try:
        logger.info(f"Preparing installation for artifact: {artifact_id}")
        
        # Get artifact details
        async with WaveMakerAPIClient() as client:
            artifact = await client.get_artifact_details(artifact_id)
        
        if not artifact:
            return {
                "success": False,
                "error": f"Artifact with ID '{artifact_id}' not found"
            }
        
        # Use unified installer
        installer = ArtifactInstaller()
        install_plan = await installer.prepare_installation(artifact, project_path)
        
        return install_plan.dict()
        
    except Exception as e:
        logger.error(f"Error preparing artifact installation: {e}")
        return {
            "success": False,
            "error": str(e)
        }

@mcp.tool(
    description="""
    List all artifacts of a given type currently installed in a WaveMaker project.

    Inputs:
    - artifact_type: The type of artifacts to list. One of "wmx", "prefab", "connector", "theme".
    - base_path: The absolute file system path to the root of the WaveMaker project (the directory that contains `.wmproject.properties`). Do not pass the subdirectory for the artifact type or the artifact directory itself.

    Behavior:
    - The tool will look in the appropriate configured subdirectory for the requested artifact type (e.g., for connectors, it will search `src/main/webapp/WEB-INF/connectors/` under the project root).
    - Returns a list of all artifacts of the specified type currently installed in the given project.

    Typical usage:
    - To list connectors for a project at `/Users/jane/WaveMakerProject`, use:
    {"artifact_type": "connector", "base_path": "/Users/jane/WaveMakerProject"}

    Notes:
    - The `base_path` must point to the project root (not to the artifact folder or a subdirectory).
    - If the project path is not correct, or if the project is missing a valid structure, the tool will report an error.
    """
)
async def list_installed_artifacts(
    artifact_type: Annotated[
        Literal["wmx", "prefab", "connector", "theme"], 
        Field(description="Type of artifacts to list")
    ],
    base_path: Annotated[
        str, 
        Field(description="Base path of the WaveMaker project to search for installed artifacts")
    ]
    ) -> Dict[str, Any]:
    """
    List all installed artifacts of the given type in a WaveMaker project.

    Parameters:
    - artifact_type (str): One of "wmx", "prefab", "connector", or "theme". This determines which type of artifacts to list.
    - base_path (str): Path to the root directory of the WaveMaker project (must contain `.wmproject.properties`). The tool will find the correct subdirectory for the artifact type automatically.

    Example:
    To list connectors for a project at '/Users/alex/WaveMakerApp', call:
    {
        "artifact_type": "connector",
        "base_path": "/Users/alex/WaveMakerApp"
    }

    Returns:
    - installed_artifacts: List of installed artifacts with their metadata.
    - total_count: Count of installed artifacts.
    - error: Present only if something went wrong (e.g., wrong path, type, or project misconfiguration).

    Note:
    Pass only the project root, not the target artifact subdirectory.
    """
    try:
        installer = ArtifactInstaller()
        return await installer.list_installed_artifacts(artifact_type, base_path)
        
    except Exception as e:
        logger.error(f"Error listing installed artifacts: {e}")
        return {
            "error": str(e),
            "installed_artifacts": [],
            "total_count": 0
        }

# @mcp.tool(
#     description="Check if the current WaveMaker project is compatible with specific artifact types. Use this before installation.",
# )
# async def check_project_compatibility(artifact_type: Optional[str] = None,project_path: Optional[str] = None) -> Dict[str, Any]:
#     """
#     Check if current project is compatible with specific artifact types
    
#     Args:
#         artifact_type: Type of artifact to check compatibility for (optional)
        
#     Returns:
#         Dictionary containing project compatibility information
#     """
#     try:
#         installer = ArtifactInstaller()
#         is_rn_project = installer._is_react_native_wm_project(project_path)
        
#         # Project type information
#         project_info = {
#             "is_react_native_wavemaker_project": is_rn_project,
#             "rn_config_file_path": "src/main/webapp/wm_rn_config.json",
#             "rn_config_file_exists": Path("src/main/webapp/wm_rn_config.json").exists()
#         }
        
#         # Compatibility matrix
#         compatibility = {
#             "wmx": {
#                 "compatible": is_rn_project,
#                 "reason": "WMX components require React Native WaveMaker projects" if not is_rn_project else "Compatible"
#             },
#             "prefab": {
#                 "compatible": True,
#                 "reason": "Prefabs are compatible with all WaveMaker projects"
#             },
#             "connector": {
#                 "compatible": True,
#                 "reason": "Connectors are compatible with all WaveMaker projects"
#             },
#             "theme": {
#                 "compatible": True,
#                 "reason": "Themes are compatible with all WaveMaker projects"
#             }
#         }
        
#         result = {
#             "project_info": project_info,
#             "compatibility": compatibility
#         }
        
#         # If specific artifact type requested
#         if artifact_type:
#             if artifact_type in compatibility:
#                 result["requested_artifact_compatibility"] = compatibility[artifact_type]
#             else:
#                 result["error"] = f"Unknown artifact type: {artifact_type}"
        
#         return result
        
#     except Exception as e:
#         logger.error(f"Error checking project compatibility: {e}")
#         return {
#             "error": str(e),
#             "project_info": {},
#             "compatibility": {}
#         }

@mcp.tool(
    description="Build a connector artifact using Maven. Use this for connectors that need to be compiled from source.",
)
async def build_connector_artifact(
    repo_path: Annotated[
        str, 
        Field(description="Local file system path to the cloned connector repository containing pom.xml")
    ]
    ) -> Dict[str, Any]:
    """
    Build a connector artifact using Maven
    
    Args:
        repo_path: Path to the cloned connector repository
        
    Returns:
        Dictionary containing build results
    """
    try:
        installer = ArtifactInstaller()
        return await installer.build_connector(repo_path)
        
    except Exception as e:
        logger.error(f"Error building connector: {e}")
        return {
            "success": False,
            "error": str(e)
        }


# # Add this function outside the tool decorators
# async def _execute_actions_internal(actions: List[Dict[str, Any]]) -> Dict[str, Any]:
#     """Internal function to execute installation actions"""
#     import tempfile
    
#     try:
#         executed_actions = []
#         errors = []
        
#         for action in actions:
#             action_type = action.get("action")
            
#             if action_type == "create_directory":
#                 try:
#                     os.makedirs(action["path"], exist_ok=True)
#                     executed_actions.append(f"Created directory: {action['path']}")
#                 except Exception as e:
#                     errors.append(f"Failed to create directory {action['path']}: {str(e)}")
                    
#             elif action_type == "download_and_extract":
#                 try:
#                     # ✅ Use a temporary directory instead of current working directory
#                     with tempfile.TemporaryDirectory() as temp_dir:
#                         temp_zip_path = Path(temp_dir) / f"temp_{action['artifact_name']}.zip"
                        
#                         # Download ZIP file
#                         response = requests.get(action["source_url"])
#                         response.raise_for_status()
                        
#                         # Save to temporary file in temp directory
#                         with open(temp_zip_path, "wb") as f:
#                             f.write(response.content)
                        
#                         # Extract to target directory
#                         with zipfile.ZipFile(temp_zip_path, "r") as zip_ref:
#                             zip_ref.extractall(action["target_path"])
                        
#                         # No need to manually cleanup - TemporaryDirectory handles it
#                         executed_actions.append(f"Downloaded and extracted: {action['source_url']} -> {action['target_path']}")
                        
#                 except Exception as e:
#                     errors.append(f"Failed to download/extract {action['source_url']}: {str(e)}")
                    
#             elif action_type == "write_file":
#                 try:
#                     # Create parent directories
#                     file_path = Path(action["path"])
#                     file_path.parent.mkdir(parents=True, exist_ok=True)
                    
#                     # Write file content
#                     if action.get("is_binary", False):
#                         content_bytes = base64.b64decode(action["content"])
#                         with open(file_path, "wb") as f:
#                             f.write(content_bytes)
#                     else:
#                         with open(file_path, "w", encoding="utf-8") as f:
#                             f.write(action["content"])
                            
#                     executed_actions.append(f"Created file: {action['path']}")
                    
#                 except Exception as e:
#                     errors.append(f"Failed to write file {action['path']}: {str(e)}")
            
#             else:
#                 errors.append(f"Unknown action type: {action_type}")
        
#         return {
#             "success": len(errors) == 0,
#             "executed_actions": executed_actions,
#             "errors": errors,
#             "total_actions": len(actions),
#             "successful_actions": len(executed_actions)
#         }
        
#     except Exception as e:
#         return {
#             "success": False,
#             "error": f"Execution failed: {str(e)}",
#             "executed_actions": [],
#             "errors": [str(e)]
#         }

# # Update the tool to use the shared function
# @mcp.tool(
#     description="Execute installation actions from a prepared installation plan. Use this after getting installation plan to actually perform the installation."
# )
# async def execute_installation_actions(
#     actions: Annotated[
#         List[Dict[str, Any]],
#         Field(description="List of structured actions to execute (from installation plan)")
#     ]
# ) -> Dict[str, Any]:
#     """Execute structured installation actions on the MCP server side"""
#     return await _execute_actions_internal(actions)

# # Update the complete installation tool to use the shared function
# @mcp.tool(
#     description="Install artifact directly - handles both planning and execution automatically"
# )
# async def install_artifact_complete(
#     artifact_id: Annotated[str, Field(description="Artifact ID to install")],
#     project_path: Annotated[Optional[str], Field(description="Path to the WaveMaker project where the artifact should be installed. If not provided, uses current working directory.")] = None
# ) -> Dict[str, Any]:
#     """
#     Prepare artifact installation by analyzing files and project modifications needed
    
#     Args:
#         artifact_id: Unique identifier of the artifact to install
#         project_path: Project Path, it is path of the project where artifact is to be installed
        
#         Returns:
#             Dictionary containing installation plan with files and project modifications
#         """
#     try:
#         # Get installation plan
#         installer = ArtifactInstaller()
#         async with WaveMakerAPIClient() as client:
#             artifact = await client.get_artifact_details(artifact_id)
#             if not artifact:
#                 return {"success": False, "error": f"Artifact {artifact_id} not found"}

#         install_plan = await installer.prepare_installation(artifact, project_path)
#         if not install_plan.success:
#             return install_plan.dict()

#         # Execute the plan automatically using the shared function
#         if install_plan.actions:
#             execution_result = await _execute_actions_internal(install_plan.actions)  # ✅ Call shared function
#             if not execution_result["success"]:
#                 return {
#                     "success": False,
#                     "error": "Installation execution failed",
#                     "execution_details": execution_result
#                 }

#         return {
#             "success": True,
#             "message": f"Successfully installed {artifact.name}",
#             # "installation_plan": install_plan.dict(),
#             "execution_result": execution_result
#         }
        
#     except Exception as e:
#         return {"success": False, "error": str(e)}

if __name__ == "__main__":
    mcp.run(transport="http", host="127.0.0.1", port=8000)
