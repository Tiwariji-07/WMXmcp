"""
Unified artifact installer for all marketplace artifact types
"""
import json
import logging
import tempfile
import requests
from urllib.parse import urlparse
import os
import zipfile
import subprocess
import asyncio
from pathlib import Path
from typing import List, Optional, Dict, Any
from datetime import datetime
import hashlib

from models import (
    BaseArtifact, WMXComponent, Prefab, Connector, Theme, ArtifactType,
    ArtifactInstallPlan, ArtifactInstallResult
)
from git_manager import GitManager
from config import settings

logger = logging.getLogger(__name__)


class ArtifactInstaller:
    """Unified installer for all artifact types"""
    
    def __init__(self):
        self.git_manager = GitManager()
        
        # Define base paths for different artifact types - centralized from config
        self.artifact_paths = {
            ArtifactType.WMX_COMPONENT: settings.wmx_component_base_path,
            ArtifactType.PREFAB: settings.prefab_base_path,
            ArtifactType.CONNECTOR: settings.connector_base_path,
            ArtifactType.THEME: settings.theme_base_path
        }
    
    def _is_wavemaker_project(self, target_path: Optional[str] = None) -> bool:
        """
        Check if the target directory or its parent directories contain .wmproject.properties
        """
        if target_path:
            # Start from target path and go up to find project root
            current = Path(target_path)
            while current != current.parent:  # Stop at filesystem root
                if (current / ".wmproject.properties").exists():
                    return True
                current = current.parent
            return False
        else:
            # Check current working directory
            return Path(".wmproject.properties").exists()

    
    def _is_react_native_wm_project(self, target_path: Optional[str] = None) -> bool:
        """
        Check if the current project is a React Native WaveMaker project
        by looking for the wm_rn_config.json file
        """
        rn_config_path = Path(target_path, "src/main/webapp/wm_rn_config.json")
        return rn_config_path.exists()
    
    async def prepare_installation(self,artifact: BaseArtifact,target_path: Optional[str] = None) -> ArtifactInstallPlan:
        """
        Prepare installation plan for any artifact type
        
        Args:
            artifact: Artifact to install
            target_path: Custom installation path (optional)
            
        Returns:
            Installation plan with files and project modifications
        """
        try:
            logger.info(f"Preparing installation for {artifact.artifact_type.value}: {artifact.name}")
            
            # 1. Check if this is a WaveMaker project
            if not self._is_wavemaker_project(target_path):
                return ArtifactInstallPlan(
                    success=False,
                    artifact={},
                    target_path="",

                    error="This is not a valid WaveMaker project. The file '.wmproject.properties' was not found at the project root. "
                           "Only WaveMaker projects can have marketplace artifacts installed.",
                    instructions=""
                )
            
            # 2. Check if WMX component is being installed on non-RN project
            if artifact.artifact_type == ArtifactType.WMX_COMPONENT and not self._is_react_native_wm_project(target_path):
                return ArtifactInstallPlan(
                        success=False,
                        artifact={},
                        target_path="",
                        error="WMX components can only be installed in React Native WaveMaker projects. "
                               "This project does not appear to be a React Native WaveMaker project "
                               "(missing src/main/webapp/wm_rn_config.json file). "
                               "WMX components are specifically designed for React Native applications and "
                               "require the React Native runtime environment to function properly.",
                        instructions=""
                    )
            base_path = ""
            if target_path:
                # If target_path is provided, treat it as project root and build proper artifact path
                project_root = self._get_project_root_from_target(target_path)
                relative_artifact_path = self.artifact_paths.get(
                    artifact.artifact_type,
                    self.artifact_paths[ArtifactType.WMX_COMPONENT]
                )
                base_path = Path(project_root) / relative_artifact_path
            else:
                base_path = self.artifact_paths.get(
                    artifact.artifact_type,
                    self.artifact_paths[ArtifactType.WMX_COMPONENT]
                )

            artifact_path = Path(base_path) / artifact.name
            
            # Check if artifact already exists
            if artifact_path.exists():
                return ArtifactInstallPlan(
                    success=False,
                    artifact={},
                    target_path=str(artifact_path),
                    error=f"{artifact.artifact_type.value.upper()} '{artifact.name}' already exists at {artifact_path}",
                    instructions=""
                )
            if hasattr(artifact, 'source_url') and artifact.source_url and artifact.artifact_type != ArtifactType.WMX_COMPONENT:
                logger.info(f"Found source_url for {artifact.name}: {artifact.source_url}")
                install_plan = await self._prepare_source_url_installation(artifact, str(artifact_path))
            else:
                # Clone repository to temporary directory
                temp_dir = await self._prepare_artifact_files(artifact)
            
                try:
                    # Handle connector-specific installation logic
                    if artifact.artifact_type == ArtifactType.CONNECTOR:
                        install_plan = await self._prepare_connector_installation(
                            artifact, str(artifact_path), temp_dir
                        )
                    else:
                        # Get all files from the repository (for other artifact types)
                        artifact_files = self._get_artifact_files(temp_dir)
                        
                        # Create installation plan based on artifact type
                        install_plan = await self._create_install_plan(
                            artifact, str(artifact_path), artifact_files
                        )
                    
                    
                finally:
                    # Cleanup temporary directory
                    self.git_manager.cleanup_temp(temp_dir)
            return install_plan
        except Exception as e:
            logger.error(f"Error preparing {artifact.artifact_type.value} installation: {e}")
            return ArtifactInstallPlan(
                success=False,
                artifact={},
                target_path="",
                error=str(e),
                instructions=""
            )
    
    async def _prepare_connector_installation(self,artifact: Connector,target_path: str,temp_dir: str) -> ArtifactInstallPlan:
        """
        Special handling for connector installations - auto-build if needed
        """
        repo_path = Path(temp_dir)
        dist_path = repo_path / "dist"
        
        # Prepare basic artifact info
        artifact_info = {
            "id": artifact.id,
            "name": artifact.name,
            "display_name": artifact.display_name,
            "description": artifact.description,
            "artifact_type": artifact.artifact_type.value,
            "version": artifact.version,
            "category": artifact.category,
            "tags": artifact.tags
        }
        
        files_to_create = []
        
        # 1. Check for existing dist with zip
        if dist_path.exists():
            zip_files = list(dist_path.glob("*.zip"))
            if zip_files:
                zip_file = zip_files[0]
                logger.info(f"Found pre-built distribution zip: {zip_file}")
                files_to_create = await self._extract_connector_zip(zip_file, artifact.name)
            else:
                # dist exists but no zip - build needed
                logger.info("dist folder exists but no zip found. Building connector...")
                build_result = await self._build_connector_in_mcp(repo_path)
                if not build_result["success"]:
                    return ArtifactInstallPlan(
                        success=False,
                        artifact=artifact_info,
                        target_path=target_path,
                        error=f"Failed to build connector: {build_result.get('error', 'Build failed')}",
                        instructions=""
                    )
                
                # Check for zip after build
                zip_files = list(dist_path.glob("*.zip"))
                if zip_files:
                    files_to_create = await self._extract_connector_zip(zip_files[0], artifact.name)
                else:
                    return ArtifactInstallPlan(
                        success=False,
                        artifact=artifact_info,
                        target_path=target_path,
                        error="Build completed but no distribution zip was created in dist/ folder",
                        instructions=""
                    )
        else:
            # No dist folder - build needed
            logger.info("No dist folder found. Building connector from source...")
            build_result = await self._build_connector_in_mcp(repo_path)
            if not build_result["success"]:
                return ArtifactInstallPlan(
                    success=False,
                    artifact=artifact_info,
                    target_path=target_path,
                    error=f"Failed to build connector: {build_result.get('error', 'Build failed')}",
                    instructions=""
                )
            
            # Check for created dist and zip
            if dist_path.exists():
                zip_files = list(dist_path.glob("*.zip"))
                if zip_files:
                    files_to_create = await self._extract_connector_zip(zip_files[0], artifact.name)
                else:
                    return ArtifactInstallPlan(
                        success=False,
                        artifact=artifact_info,
                        target_path=target_path,
                        error="Build completed but no distribution zip was created",
                        instructions=""
                    )
            else:
                return ArtifactInstallPlan(
                    success=False,
                    artifact=artifact_info,
                    target_path=target_path,
                    error="Build completed but dist/ folder was not created",
                    instructions=""
                )
        
        # Add metadata file
        metadata_content = json.dumps({
            "id": artifact.id,
            "name": artifact.name,
            "artifact_type": artifact.artifact_type.value,
            "version": artifact.version,
            "installed_at": datetime.now().isoformat(),
            "source_url": str(artifact.git_url),
            "description": artifact.description,
            "author": artifact.author.dict(),
            "built_by_mcp": True  # Indicates this was built by MCP
        }, indent=2)
        
        files_to_create.append({
            "path": f"{artifact.name}/.connector-metadata.json",
            "content": metadata_content,
            "description": "CONNECTOR metadata file",
            "is_binary": False,
            "size": len(metadata_content)
        })

        # Create structured actions
        actions = self._create_structured_actions(target_path, files_to_create)
        
        instructions = f"""CONNECTOR '{artifact.name}' Installation PLAN GENERATED:

        - {len(files_to_create)} files are ready to be created in: {target_path}/
        - No actual files have been copied or modified yet.

        To COMPLETE INSTALLATION:
        - Apply this installation plan by writing each file to its corresponding location.

        Installation Summary:
        - Artifact: {artifact.name} (v{artifact.version})
        - Type: CONNECTOR (Auto-built by MCP)
        - Plan Status: READY (Not installed)

        Write the files to the target path to complete the installation.
        """

        return ArtifactInstallPlan(
            success=True,
            artifact=artifact_info,
            target_path=target_path,
            actions=actions,
            files_to_create=files_to_create,
            project_modifications=[],  # No additional modifications needed
            instructions=instructions
        )

    async def _build_connector_in_mcp(self, repo_path: Path) -> Dict[str, Any]:
        """
        Build connector distribution using Maven within MCP environment
        """
        try:
            logger.info(f"Building connector at: {repo_path}")
            
            # Check for Maven build file
            if not (repo_path / "pom.xml").exists():
                return {
                    "success": False,
                    "error": "No pom.xml found. Connector must be a Maven project for auto-build."
                }
            
            # Run Maven build
            result = await self._run_build_command("mvn clean install", str(repo_path))
            
            if result["success"]:
                logger.info("Connector build completed successfully")
                return {
                    "success": True,
                    "message": "Build successful",
                    "output": result.get("output", "")
                }
            else:
                logger.error(f"Connector build failed: {result.get('error', '')}")
                return {
                    "success": False,
                    "error": f"Build failed: {result.get('error', 'Unknown error')}",
                    "output": result.get("output", "")
                }
                
        except Exception as e:
            logger.error(f"Error building connector: {e}")
            return {
                "success": False,
                "error": f"Build system error: {str(e)}"
            }

    async def _extract_connector_zip(self, zip_path: Path, artifact_name: str) -> List[Dict[str, Any]]:
        """Extract connector zip and return file contents"""
        import base64
        
        files_to_create = []
        try:
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                for file_info in zip_ref.infolist():
                    if file_info.is_dir():
                        continue
                    
                    try:
                        with zip_ref.open(file_info) as file:
                            content = file.read()
                            
                            # Try to decode as text
                            try:
                                text_content = content.decode('utf-8')
                                files_to_create.append({
                                    "path": f"{artifact_name}/{file_info.filename}",
                                    "content": text_content,
                                    "description": f"CONNECTOR file: {file_info.filename}",
                                    "is_binary": False,
                                    "size": len(content)
                                })
                            except UnicodeDecodeError:
                                # Binary file - encode as base64
                                content_b64 = base64.b64encode(content).decode('utf-8')
                                files_to_create.append({
                                    "path": f"{artifact_name}/{file_info.filename}",
                                    "content": content_b64,  # ✅ ACTUAL CONTENT AS BASE64
                                    "description": f"CONNECTOR binary file: {file_info.filename}",
                                    "is_binary": True,
                                    "size": len(content)  # Original binary size
                                })
                    except Exception as e:
                        logger.warning(f"Could not read file {file_info.filename} from zip: {e}")
        except Exception as e:
            logger.error(f"Error extracting connector zip {zip_path}: {e}")
        
        return files_to_create

    async def build_connector(self, repo_path: str) -> Dict[str, Any]:
        """
        Build connector using Maven - this would be called by the IDE/user after preparation
        """
        try:
            repo_path = Path(repo_path)
            
            # Run mvn clean install
            result = await self._run_build_command("mvn clean install", str(repo_path))
            
            if result["success"]:
                # Check if dist folder was created with zip
                dist_path = repo_path / "dist"
                if dist_path.exists():
                    zip_files = list(dist_path.glob("*.zip"))
                    if zip_files:
                        return {
                            "success": True,
                            "message": f"Build successful. Distribution created: {zip_files[0].name}",
                            "dist_zip": str(zip_files)
                        }
                
                return {
                    "success": False,
                    "message": "Build completed but no distribution zip found in dist folder",
                    "build_output": result.get("output", "")
                }
            else:
                return result
                
        except Exception as e:
            logger.error(f"Error building connector: {e}")
            return {
                "success": False,
                "message": f"Build failed: {str(e)}"
            }
    
    async def _run_build_command(self, command: str, working_dir: str) -> Dict[str, Any]:
        """Run build command asynchronously"""
        try:
            process = await asyncio.create_subprocess_shell(
                command,
                cwd=working_dir,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            return {
                "success": process.returncode == 0,
                "return_code": process.returncode,
                "output": stdout.decode() if stdout else "",
                "error": stderr.decode() if stderr else "",
                "command": command,
                "working_directory": working_dir
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "command": command,
                "working_directory": working_dir
            }
    
    async def list_installed_artifacts(self, artifact_type: Optional[str] = None, base_path: Optional[str] = None) -> Dict[str, Any]:
        """List all installed artifacts in the project"""
        try:
            installed_artifacts = []
            
            # Determine which paths to search
            paths_to_search = {}
            if artifact_type:
                try:
                    artifact_type_enum = ArtifactType(artifact_type)
                    paths_to_search[artifact_type_enum] = self.artifact_paths[artifact_type_enum]
                except ValueError:
                    return {
                        "error": f"Invalid artifact type: {artifact_type}",
                        "installed_artifacts": [],
                        "total_count": 0
                    }
            else:
                paths_to_search = self.artifact_paths

            # Search each path for installed artifacts
            for artifact_type_enum, relative_path in paths_to_search.items():
                if base_path:
                    # Use base_path + relative artifact path
                    search_path = Path(base_path) / relative_path
                else:
                    # Use absolute path from config
                    if relative_path is None:  # ✅ Add this check
                        logger.warning(f"No path configured for artifact type: {artifact_type_enum}")
                        continue
                    search_path = Path(relative_path)
                
                if not search_path.exists():
                    logger.debug(f"Search path does not exist: {search_path}")
                    continue
                    
                # Find artifacts in this directory
                for artifact_dir in search_path.iterdir():
                    if artifact_dir.is_dir() and not artifact_dir.name.startswith('.'):
                        artifact_info = await self._get_artifact_info(artifact_dir, artifact_type_enum)
                        if artifact_info:
                            installed_artifacts.append(artifact_info)

            # Add project type information to the response
            project_info = {
                "is_wavemaker_project": self._is_wavemaker_project(base_path),  # ✅ Pass base_path
                "wmproject_properties_exists": Path(base_path, ".wmproject.properties").exists() if base_path else Path(".wmproject.properties").exists(),
                "is_react_native_project": self._is_react_native_wm_project(base_path),  # ✅ Pass base_path
                "rn_config_file_exists": Path(base_path, "src/main/webapp/wm_rn_config.json").exists() if base_path else Path("src/main/webapp/wm_rn_config.json").exists()
            }

            return {
                "installed_artifacts": installed_artifacts,
                "total_count": len(installed_artifacts),
                "search_paths": {k.value: str(Path(base_path) / v) if base_path and v else v for k, v in paths_to_search.items()},
                "project_info": project_info
            }

        except Exception as e:
            logger.error(f"Error listing installed artifacts: {e}")
            return {
                "error": str(e),
                "installed_artifacts": [],
                "total_count": 0
            }

    async def _prepare_artifact_files(self, artifact: BaseArtifact) -> str:
        """Clone artifact repository to temporary directory"""
        temp_dir = tempfile.mkdtemp(prefix=f"{artifact.artifact_type.value}_{artifact.name}_")
        await self.git_manager._clone_repository(
            str(artifact.git_url), temp_dir, artifact.git_branch
        )
        
        # If there's a specific path within the repo, adjust the temp_dir
        if artifact.git_path:
            specific_path = Path(temp_dir) / artifact.git_path
            if specific_path.exists():
                # Create a new temp directory with just the specific path contents
                new_temp_dir = tempfile.mkdtemp(prefix=f"{artifact.artifact_type.value}_{artifact.name}_specific_")
                import shutil
                shutil.copytree(specific_path, Path(new_temp_dir) / "content")
                shutil.rmtree(temp_dir)
                return str(Path(new_temp_dir) / "content")
        
        return temp_dir
    
    def _create_structured_actions(self, target_path: str, files_to_create: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Create structured, machine-readable actions"""
        actions = []
    
        # 1. Directory creation action
        actions.append({
            "action": "create_directory",
            "path": target_path,
            "required": True
        })
    
        # 2. File creation actions
        for file_info in files_to_create:
            # Remove artifact name prefix from path
            relative_path = file_info["path"]
            if "/" in relative_path:
                relative_path = "/".join(relative_path.split("/")[1:])
            
            full_path = f"{target_path}/{relative_path}"
            
            # Generate checksum for verification
            content_for_hash = file_info["content"].encode('utf-8')
            checksum = hashlib.sha256(content_for_hash).hexdigest()
            
            actions.append({
                "action": "write_file",
                "path": full_path,
                "content": file_info["content"],
                "encoding": "base64" if file_info.get("is_binary", False) else "utf-8",
                "is_binary": file_info.get("is_binary", False),
                "checksum": checksum,
                "size": file_info["size"],
                "description": file_info["description"]
            })
        
        return actions

    def _get_artifact_files(self, temp_dir: str) -> List[Dict[str, Any]]:
        """Get all artifact files with their content (reuses git_manager logic)"""
        return self.git_manager.get_component_files(temp_dir)
    
    async def _create_install_plan(self,artifact: BaseArtifact,target_path: str,artifact_files: List[Dict[str, Any]]) -> ArtifactInstallPlan:
        """Create installation plan based on artifact type"""
        
        # Prepare basic artifact info
        artifact_info = {
            "id": artifact.id,
            "name": artifact.name,
            "display_name": artifact.display_name,
            "description": artifact.description,
            "artifact_type": artifact.artifact_type.value,
            "version": artifact.version,
            "category": artifact.category,
            "tags": artifact.tags
        }
        
        # Prepare files to create
        files_to_create = []
        for file_info in artifact_files:
            files_to_create.append({
                "path": f"{artifact.name}/{file_info['relative_path']}",
                "content": file_info["content"],
                "description": f"{artifact.artifact_type.value.upper()} file: {file_info['relative_path']}",
                "is_binary": file_info.get("is_binary", False),
                "size": file_info["size"]
            })
        
        # Add metadata file
        metadata_content = json.dumps({
            "id": artifact.id,
            "name": artifact.name,
            "artifact_type": artifact.artifact_type.value,
            "version": artifact.version,
            "installed_at": datetime.now().isoformat(),
            "source_url": str(artifact.git_url),
            "description": artifact.description,
            "author": artifact.author.dict()
        }, indent=2)
        
        files_to_create.append({
            "path": f"{artifact.name}/.{artifact.artifact_type.value}-metadata.json",
            "content": metadata_content,
            "description": f"{artifact.artifact_type.value.upper()} metadata file",
            "is_binary": False,
            "size": len(metadata_content)
        })
        
        # Get artifact-type specific project modifications (simplified for WMX)
        project_modifications = await self._get_project_modifications(artifact)
        # Create structured actions
        actions = self._create_structured_actions(target_path, files_to_create)
        # Create installation instructions
        instructions = self._create_installation_instructions(artifact, target_path, files_to_create, project_modifications)
        
        return ArtifactInstallPlan(
            success=True,
            artifact=artifact_info,
            target_path=target_path,
            files_to_create=files_to_create,
            actions=actions,
            project_modifications=project_modifications,
            instructions=instructions
        )
    
    async def _get_project_modifications(self, artifact: BaseArtifact) -> List[Dict[str, Any]]:
        """Get project modifications needed for each artifact type"""
        
        if artifact.artifact_type == ArtifactType.WMX_COMPONENT:
            return await self._get_wmx_project_modifications(artifact)
        elif artifact.artifact_type == ArtifactType.PREFAB:
            return await self._get_prefab_project_modifications(artifact)
        elif artifact.artifact_type == ArtifactType.CONNECTOR:
            return await self._get_connector_project_modifications(artifact)
        elif artifact.artifact_type == ArtifactType.THEME:
            return await self._get_theme_project_modifications(artifact)
        else:
            return []
    
    async def _get_wmx_project_modifications(self, artifact: WMXComponent) -> List[Dict[str, Any]]:
        """Get project modifications needed for WMX components - SIMPLIFIED"""
        # For WMX components, no config changes needed - just copy files
        # Return empty list as no project modifications are required
        return []
    
    async def _get_prefab_project_modifications(self, artifact: Prefab) -> List[Dict[str, Any]]:
        """Get project modifications needed for Prefabs"""
        # Placeholder for prefab-specific modifications
        return [
            {
                "type": "placeholder",
                "description": "Prefab project modifications will be implemented here",
                "artifact_type": "prefab",
                "artifact_name": artifact.name,
                "required": False
            }
        ]
    
    async def _get_connector_project_modifications(self, artifact: Connector) -> List[Dict[str, Any]]:
        """Get project modifications needed for Connectors"""
        # Placeholder for connector-specific modifications
        return [
            {
                "type": "placeholder",
                "description": "Connector project modifications will be implemented here",
                "artifact_type": "connector",
                "artifact_name": artifact.name,
                "required": False
            }
        ]
    
    async def _get_theme_project_modifications(self, artifact: Theme) -> List[Dict[str, Any]]:
        """Get project modifications needed for Themes"""
        # Placeholder for theme-specific modifications
        return [
            {
                "type": "placeholder",
                "description": "Theme project modifications will be implemented here",
                "artifact_type": "theme",
                "artifact_name": artifact.name,
                "required": False
            }
        ]
    
    def _create_installation_instructions(self,artifact: BaseArtifact,target_path: str,files_to_create: List[Dict[str, Any]],project_modifications: List[Dict[str, Any]]) -> str:
        """Create human-readable installation instructions"""
        
        instructions = f"""To install the {artifact.artifact_type.value.upper()} '{artifact.display_name}':
        1. Create the directory: {target_path}/
        2. Copy {len(files_to_create)} files from the repository to this directory
        """
        
        if artifact.artifact_type == ArtifactType.WMX_COMPONENT:
            instructions += """3. No additional configuration changes required
            4. The WMX component will be available in your React Native components directory
            5. You can now use this component in your React Native WaveMaker project

            ⚠️  Note: WMX components are only compatible with React Native WaveMaker projects.
            """
        else:
            if project_modifications:
                instructions += f"3. Apply {len(project_modifications)} project configuration changes:\n"
                for i, mod in enumerate(project_modifications, 1):
                    if mod.get("type") != "placeholder":
                        instructions += f"   - {mod.get('description', f'Modification {i}')}\n"
            
            instructions += f"""4. Restart the WaveMaker application server if needed
            5. The {artifact.artifact_type.value.upper()} will be available in your project
            """
        
        instructions += f"""
            Installation Summary:
            - Artifact: {artifact.display_name} (v{artifact.version})
            - Type: {artifact.artifact_type.value.upper()}
            - Files: {len([f for f in files_to_create if not f.get('is_binary', False)])} source files
            - Target: {target_path}
            - Configuration Path: {self.artifact_paths.get(artifact.artifact_type, 'Unknown')}
            """
        
        if artifact.artifact_type == ArtifactType.WMX_COMPONENT:
            instructions += "- Project Type: React Native WaveMaker (Required for WMX components)"
        
        return instructions
    
    async def _get_artifact_info(self,artifact_dir: Path,artifact_type: ArtifactType) -> Optional[Dict[str, Any]]:
        """Get information about an installed artifact"""
        try:
            metadata_file = artifact_dir / f".{artifact_type.value}-metadata.json"
            
            artifact_info = {
                "name": artifact_dir.name,
                "path": str(artifact_dir),
                "artifact_type": artifact_type.value,
                "has_metadata": metadata_file.exists()
            }
            
            # Load metadata if available
            if metadata_file.exists():
                try:
                    with open(metadata_file, 'r') as f:
                        metadata = json.load(f)
                        artifact_info.update({
                            "id": metadata.get("id"),
                            "version": metadata.get("version"),
                            "description": metadata.get("description"),
                            "author": metadata.get("author", {}).get("name"),
                            "installed_at": metadata.get("installed_at"),
                            "source_url": metadata.get("source_url")
                        })
                except Exception as e:
                    logger.warning(f"Failed to read metadata for {artifact_dir.name}: {e}")
            
            # Also check for artifact-specific config files
            if artifact_type == ArtifactType.WMX_COMPONENT:
                wmconfig_file = artifact_dir / "wmconfig.json"
                if wmconfig_file.exists():
                    try:
                        with open(wmconfig_file, 'r') as f:
                            wmconfig = json.load(f)
                            artifact_info.update({
                                "display_name": wmconfig.get("displayName"),
                                "config_version": wmconfig.get("version")
                            })
                    except Exception:
                        pass
            
            return artifact_info
            
        except Exception as e:
            logger.error(f"Error getting artifact info for {artifact_dir}: {e}")
            return None

    def _get_project_root_from_target(self, target_path: str) -> str:
        """
        Extract project root directory from target installation path
        """
        target = Path(target_path)
    
        # Look for project root by going up the directory tree
        current = target
        while current != current.parent:  # Stop at filesystem root
            if (current / ".wmproject.properties").exists():
                return str(current)
            current = current.parent
    
        # If no .wmproject.properties found, assume target_path IS the project root
        return str(target)

    async def execute_installation(self, install_plan: ArtifactInstallPlan) -> ArtifactInstallResult:
        """
        Execute the actual installation based on the install plan
        """
        import base64
        
        try:
            target_path = Path(install_plan.target_path)
            target_path.mkdir(parents=True, exist_ok=True)
            
            installed_files = []
            
            for file_info in install_plan.files_to_create:
                # Remove artifact name prefix from path
                relative_path = file_info["path"]
                if "/" in relative_path:
                    relative_path = "/".join(relative_path.split("/")[1:])
                
                file_path = target_path / relative_path
                file_path.parent.mkdir(parents=True, exist_ok=True)
                
                if file_info.get("is_binary", False):
                    # Decode base64 and write binary content
                    try:
                        content_bytes = base64.b64decode(file_info["content"])
                        with open(file_path, 'wb') as f:
                            f.write(content_bytes)
                        logger.info(f"Created binary file: {file_path} ({len(content_bytes)} bytes)")
                    except Exception as e:
                        logger.error(f"Failed to write binary file {file_path}: {e}")
                        continue
                else:
                    # Write text content
                    with open(file_path, 'w', encoding='utf-8') as f:
                        f.write(file_info["content"])
                    logger.info(f"Created text file: {file_path}")
                
                installed_files.append(str(file_path))
            
            return ArtifactInstallResult(
                success=True,
                artifact_name=install_plan.artifact["name"],
                artifact_type=ArtifactType(install_plan.artifact["artifact_type"]),
                install_path=install_plan.target_path,
                message=f"Successfully installed {len(installed_files)} files",
                files_installed=installed_files
            )
            
        except Exception as e:
            logger.error(f"Error executing installation: {e}")
            return ArtifactInstallResult(
                success=False,
                artifact_name=install_plan.artifact.get("name", "Unknown"),
                artifact_type=ArtifactType.CONNECTOR,
                install_path=install_plan.target_path,
                message=f"Installation failed: {str(e)}",
                errors=[str(e)]
            )

    async def _prepare_source_url_installation(self, artifact: BaseArtifact, target_path: str) -> ArtifactInstallPlan:
        """Prepare installation plan for artifacts with source_url (direct download)"""
        
        artifact_info = {
            "id": artifact.id,
            "name": artifact.name,
            "display_name": artifact.display_name,
            "description": artifact.description,
            "artifact_type": artifact.artifact_type.value,
            "version": artifact.version,
            "category": artifact.category,
            "tags": artifact.tags
        }

        # Create structured actions for download-based installation
        actions = []
        
        # 1. Directory creation action
        actions.append({
            "action": "create_directory",
            "path": target_path,
            "required": True
        })
        
        # 2. Download and extract action
        actions.append({
            "action": "download_and_extract",
            "source_url": artifact.source_url,
            "target_path": target_path,
            "artifact_name": artifact.name,
            "description": f"Download and extract {artifact.artifact_type.value.upper()} from {artifact.source_url}",
            "required": True
        })
        
        # 3. Create metadata file action
        metadata_content = json.dumps({
            "id": artifact.id,
            "name": artifact.name,
            "artifact_type": artifact.artifact_type.value,
            "version": artifact.version,
            "installed_at": datetime.now().isoformat(),
            "source_url": artifact.source_url,
            "git_url": str(artifact.git_url) if artifact.git_url else None,
            "description": artifact.description,
            # "author": artifact.author.dict(),
            "installed_from": "source_url"
        }, indent=2)
        
        metadata_checksum = hashlib.sha256(metadata_content.encode('utf-8')).hexdigest()
        actions.append({
            "action": "write_file",
            "path": f"{target_path}/.{artifact.artifact_type.value}-metadata.json",
            "content": metadata_content,
            "encoding": "utf-8",
            "is_binary": False,
            "checksum": metadata_checksum,
            "size": len(metadata_content),
            "description": f"{artifact.artifact_type.value.upper()} metadata file"
        })

        instructions = f"""STRUCTURED INSTALLATION PLAN (SOURCE_URL):
        ⚠️  IMPORTANT: This is a structured installation plan with {len(actions)} executable actions.
        Execute {len(actions)} actions to install {artifact.artifact_type.value.upper()} '{artifact.display_name}':
        - 1 directory creation
        - 1 download and extract operation  
        - 1 metadata file creation

        Agent Implementation:
        import requests
        import zipfile
        import os
        from pathlib import Path

        for action in plan["actions"]:
        if action["action"] == "create_directory":
        os.makedirs(action["path"], exist_ok=True)
        elif action["action"] == "download_and_extract":
        # Download ZIP file
        response = requests.get(action["source_url"])
        with open("temp_download.zip", "wb") as f:
        f.write(response.content)

        text
            # Extract to target directory
            with zipfile.ZipFile("temp_download.zip", "r") as zip_ref:
                zip_ref.extractall(action["target_path"])
            
            # Cleanup temp file
            os.remove("temp_download.zip")
        elif action["action"] == "write_file":
            with open(action["path"], "w", encoding="utf-8") as f:
                f.write(action["content"])
        text

        Installation Summary:
        - Artifact: {artifact.display_name} (v{artifact.version})
        - Type: {artifact.artifact_type.value.upper()}
        - Source: Direct download from {artifact.source_url}
        - Target: {target_path}
        - Method: Download and extract ZIP file
        """

        return ArtifactInstallPlan(
            success=True,
            artifact=artifact_info,
            target_path=target_path,
            actions=actions,
            files_to_create=[],  # Not used for source_url method
            project_modifications=[],
            instructions=instructions
        )