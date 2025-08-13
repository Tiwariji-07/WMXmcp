"""
Git repository management for WMX component installation
"""
import os
import shutil
import tempfile
import logging
from pathlib import Path
from typing import List, Optional, Dict, Any
import asyncio
from concurrent.futures import ThreadPoolExecutor
from git import Repo
import aiofiles
from models import WMXComponent, ComponentInstallResult
from config import settings

logger = logging.getLogger(__name__)


class GitManager:
    """Manages Git operations for component installation"""
    
    def __init__(self):
        self.executor = ThreadPoolExecutor(max_workers=2)
    
    async def install_component(
        self, 
        component: WMXComponent, 
        target_base_path: str
    ) -> ComponentInstallResult:
        """
        Install a WMX component from Git repository
        
        Args:
            component: Component to install
            target_base_path: Base path where components are installed
            
        Returns:
            Installation result with success status and details
        """
        component_path = Path(target_base_path) / component.name
        temp_dir = None
        
        try:
            logger.info(f"Starting installation of component {component.name}")
            
            # Validate target path
            if component_path.exists():
                logger.warning(f"Component {component.name} already exists at {component_path}")
                return ComponentInstallResult(
                    success=False,
                    component_name=component.name,
                    install_path=str(component_path),
                    message=f"Component {component.name} already exists. Use --force to overwrite.",
                    errors=["Component directory already exists"]
                )
            
            # Create temporary directory for cloning
            temp_dir = tempfile.mkdtemp(prefix=f"wmx_{component.name}_")
            logger.debug(f"Created temporary directory: {temp_dir}")
            
            # Clone repository
            repo_path = await self._clone_repository(
                component.git_url, 
                temp_dir, 
                component.git_branch
            )
            
            # Extract component files
            source_path = Path(repo_path)
            if component.git_path:
                source_path = source_path / component.git_path
            
            if not source_path.exists():
                raise FileNotFoundError(f"Component source path not found: {source_path}")
            
            # Validate WMX component structure
            await self._validate_component_structure(source_path)
            
            # Copy component to target location
            installed_files = await self._copy_component_files(source_path, component_path)
            
            # Create component metadata file
            await self._create_component_metadata(component, component_path)
            
            logger.info(f"Successfully installed component {component.name} to {component_path}")
            
            return ComponentInstallResult(
                success=True,
                component_name=component.name,
                install_path=str(component_path),
                message=f"Component {component.name} installed successfully",
                files_installed=installed_files
            )
        
        except Exception as e:
            logger.error(f"Failed to install component {component.name}: {e}")
            
            # Cleanup partial installation
            if component_path.exists():
                try:
                    shutil.rmtree(component_path)
                except Exception as cleanup_error:
                    logger.error(f"Failed to cleanup partial installation: {cleanup_error}")
            
            return ComponentInstallResult(
                success=False,
                component_name=component.name,
                install_path=str(component_path),
                message=f"Failed to install component {component.name}",
                errors=[str(e)]
            )
        
        finally:
            # Cleanup temporary directory
            if temp_dir and os.path.exists(temp_dir):
                try:
                    shutil.rmtree(temp_dir)
                    logger.debug(f"Cleaned up temporary directory: {temp_dir}")
                except Exception as e:
                    logger.warning(f"Failed to cleanup temporary directory {temp_dir}: {e}")
    
    async def _clone_repository(self, git_url: str, target_dir: str, branch: str = "main") -> str:
        """Clone Git repository asynchronously"""
        def _sync_clone():
            logger.debug(f"Cloning repository {git_url} to {target_dir}")
            repo = Repo.clone_from(
                git_url, 
                target_dir,
                branch=branch,
                depth=settings.git_depth,
                single_branch=True
            )
            return repo.working_dir
        
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(self.executor, _sync_clone)
    
    async def _validate_component_structure(self, component_path: Path) -> None:
        """Validate that the component has required WMX structure"""
        required_files = [
            "index.ts",       # Component entry file
            "wmconfig.json",  # WMX component configuration
            "icon.svg"        # Component icon
        ]
        
        for required_file in required_files:
            file_path = component_path / required_file
            if not file_path.exists():
                logger.warning(f"Required WMX file {required_file} not found in component")
                # Don't fail installation for missing files, just warn
    
    async def _copy_component_files(self, source_path: Path, target_path: Path) -> List[str]:
        """Copy component files from source to target directory"""
        target_path.mkdir(parents=True, exist_ok=True)
        installed_files = []
        
        def _sync_copy():
            nonlocal installed_files
            for root, dirs, files in os.walk(source_path):
                # Skip .git directory
                if '.git' in dirs:
                    dirs.remove('.git')
                
                rel_root = Path(root).relative_to(source_path)
                target_root = target_path / rel_root
                target_root.mkdir(parents=True, exist_ok=True)
                
                for file in files:
                    source_file = Path(root) / file
                    target_file = target_root / file
                    
                    shutil.copy2(source_file, target_file)
                    installed_files.append(str(target_file.relative_to(target_path.parent)))
                    logger.debug(f"Copied {source_file} -> {target_file}")
        
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(self.executor, _sync_copy)
        
        return installed_files
    
    async def _create_component_metadata(self, component: WMXComponent, component_path: Path) -> None:
        """Create metadata file for the installed component"""
        metadata = {
            "id": component.id,
            "name": component.name,
            "version": component.version,
            "installed_at": "2024-08-07T13:00:00Z",  # Current timestamp
            "source_url": str(component.git_url),
            "description": component.description,
            "author": component.author.dict()
        }
        
        metadata_file = component_path / ".wmx-component-metadata.json"
        
        async with aiofiles.open(metadata_file, 'w') as f:
            import json
            await f.write(json.dumps(metadata, indent=2))
        
        logger.debug(f"Created component metadata file: {metadata_file}")
    
    # New methods for publishing support
    async def prepare_component(self, component: WMXComponent) -> str:
        """Clone component to temp directory and return temp path"""
        temp_dir = tempfile.mkdtemp(prefix=f"wmx_{component.name}_")
        await self._clone_repository(str(component.git_url), temp_dir, component.git_branch)
        return temp_dir

    def get_component_files(self, temp_dir: str) -> List[Dict[str, Any]]:
        """Get all component files with their content"""
        files = []
        source_path = Path(temp_dir)
        
        for root, dirs, filenames in os.walk(source_path):
            # Skip .git directory
            if '.git' in dirs:
                dirs.remove('.git')
                
            for filename in filenames:
                file_path = Path(root) / filename
                relative_path = file_path.relative_to(source_path)
                
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                        files.append({
                            "relative_path": str(relative_path),
                            "content": content,
                            "size": len(content)
                        })
                except UnicodeDecodeError:
                    # Handle binary files
                    with open(file_path, 'rb') as f:
                        content = f.read()
                        files.append({
                            "relative_path": str(relative_path),
                            "content": f"<binary file: {len(content)} bytes>",
                            "is_binary": True,
                            "size": len(content)
                        })
        
        return files

    def cleanup_temp(self, temp_dir: str):
        """Clean up temporary directory"""
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)
