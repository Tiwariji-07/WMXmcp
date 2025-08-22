"""
Component validation utilities for marketplace publishing
"""
import json
import logging
from pathlib import Path
from typing import Dict, Any, List
from models import ComponentValidationResult

logger = logging.getLogger(__name__)

class ComponentValidator:
    """Validates WMX components for marketplace publishing"""
    
    def __init__(self):
        # Required files for WMX React Native components
        self.required_files = {
            "index.ts": "Component entry file (React Native implementation)",
            "wmconfig.json": "WMX component configuration file",
            "icon.svg": "Component icon (SVG format)"
        }
        
        self.recommended_files = {
            "README.md": "Component documentation",
            "CHANGELOG.md": "Version history",
            "LICENSE": "License file",
            "demo.tsx": "Component demo/example page",
            "package.json": "NPM package configuration (if using external dependencies)",
            "types.ts": "TypeScript type definitions"
        }
        
        # Required fields in wmconfig.json
        self.required_wmconfig_fields = [
            "name", "displayName", "version", "description", "category"
        ]
    
    async def validate_component(
        self, 
        component_path: str, 
        strict_validation: bool = True
    ) -> ComponentValidationResult:
        """
        Validate a local WMX React Native component for marketplace publishing
        """
        try:
            component_dir = Path(component_path)
            
            if not component_dir.exists():
                return ComponentValidationResult(
                    valid=False,
                    component_name="Unknown",
                    component_path=component_path,
                    issues=[f"Component directory not found: {component_path}"],
                    marketplace_ready=False
                )
            
            result = ComponentValidationResult(
                valid=True,
                component_name=component_dir.name,
                component_path=str(component_dir),
                marketplace_ready=False
            )
            
            # Validate required files
            await self._validate_required_files(component_dir, result)
            
            # Validate wmconfig.json structure
            if (component_dir / "wmconfig.json").exists():
                await self._validate_wmconfig_json(component_dir, result)
            
            # Validate index.ts (React Native)
            if (component_dir / "index.ts").exists():
                await self._validate_index_ts(component_dir, result)
            
            # Validate icon.svg
            if (component_dir / "icon.svg").exists():
                await self._validate_icon_svg(component_dir, result)
            
            # Check for recommended files
            self._check_recommended_files(component_dir, result)
            
            # Validate component structure
            await self._validate_component_structure(component_dir, result)
            
            # Determine if marketplace ready
            result.marketplace_ready = (
                result.valid and 
                len(result.issues) == 0 and
                result.structure_valid and
                result.requirements_met.get("index.ts", False) and
                result.requirements_met.get("wmconfig.json", False) and
                result.requirements_met.get("icon.svg", False)
            )
            
            return result
            
        except Exception as e:
            logger.error(f"Error validating component: {e}")
            return ComponentValidationResult(
                valid=False,
                component_name="Unknown",
                component_path=component_path,
                issues=[f"Validation error: {str(e)}"],
                marketplace_ready=False
            )
    
    async def _validate_required_files(self, component_dir: Path, result: ComponentValidationResult):
        """Validate presence of required files"""
        for filename, description in self.required_files.items():
            file_path = component_dir / filename
            if file_path.exists():
                result.requirements_met[filename] = True
            else:
                result.requirements_met[filename] = False
                result.issues.append(f"Missing required file: {filename} ({description})")
                result.valid = False
    
    async def _validate_wmconfig_json(self, component_dir: Path, result: ComponentValidationResult):
        """Validate wmconfig.json structure and content"""
        try:
            wmconfig_path = component_dir / "wmconfig.json"
            with open(wmconfig_path, 'r', encoding='utf-8') as f:
                metadata = json.load(f)
            
            result.metadata = metadata
            
            # Check required fields
            for field in self.required_wmconfig_fields:
                if field not in metadata:
                    result.issues.append(f"Missing required field in wmconfig.json: {field}")
                    result.valid = False
                elif not metadata[field] or str(metadata[field]).strip() == "":
                    result.issues.append(f"Empty required field in wmconfig.json: {field}")
                    result.valid = False
            
            # Validate version format
            if "version" in metadata:
                version = metadata["version"]
                if not self._is_valid_version(version):
                    result.warnings.append(f"Version '{version}' should follow semantic versioning (e.g., 1.0.0)")
            
            # Check for recommended fields
            recommended_fields = ["author", "license", "tags", "dependencies", "reactNativeVersion"]
            for field in recommended_fields:
                if field not in metadata:
                    result.suggested_improvements.append(f"Consider adding '{field}' to wmconfig.json")
            
            # Validate React Native specific fields
            if "type" not in metadata:
                result.suggested_improvements.append("Consider adding 'type' field to wmconfig.json (e.g., 'component', 'widget')")
            
            if "properties" not in metadata:
                result.suggested_improvements.append("Consider adding 'properties' configuration for component props")
                
            # Check React Native version compatibility
            if "reactNativeVersion" in metadata:
                rn_version = metadata["reactNativeVersion"]
                if not self._is_valid_rn_version(rn_version):
                    result.warnings.append(f"React Native version '{rn_version}' format should be like '>=0.72.0'")
                
        except json.JSONDecodeError as e:
            result.issues.append(f"Invalid JSON in wmconfig.json: {str(e)}")
            result.valid = False
        except Exception as e:
            result.issues.append(f"Error reading wmconfig.json: {str(e)}")
            result.valid = False
    
    async def _validate_index_ts(self, component_dir: Path, result: ComponentValidationResult):
        """Validate index.ts structure and content for React Native"""
        try:
            index_ts_path = component_dir / "index.ts"
            with open(index_ts_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            if not content.strip():
                result.issues.append("index.ts appears to be empty")
                result.valid = False
                return
            
            # Basic React Native validation
            required_patterns = [
                ("export", "index.ts should have at least one export statement"),
                ("react", "index.ts should import React")
            ]
            
            content_lower = content.lower()
            for pattern, message in required_patterns:
                if pattern not in content_lower:
                    result.warnings.append(message)
            
            # Check for React Native patterns
            rn_patterns = [
                "react-native",
                "view",
                "text",
                "touchableopacity",
                "component",
                "props"
            ]
            
            if not any(pattern in content_lower for pattern in rn_patterns):
                result.warnings.append("index.ts doesn't seem to follow React Native component patterns")
            
            # Check for proper React Native imports
            react_imports = [
                "from 'react'",
                "from 'react-native'"
            ]
            
            if not any(import_stmt in content_lower for import_stmt in react_imports):
                result.warnings.append("Consider importing React and React Native components")
                
        except Exception as e:
            result.warnings.append(f"Could not validate index.ts content: {str(e)}")
    
    async def _validate_icon_svg(self, component_dir: Path, result: ComponentValidationResult):
        """Validate icon.svg file"""
        try:
            icon_path = component_dir / "icon.svg"
            with open(icon_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            if not content.strip():
                result.issues.append("icon.svg appears to be empty")
                result.valid = False
                return
            
            # Basic SVG validation
            if not content.strip().startswith('<svg'):
                result.warnings.append("icon.svg should start with <svg> tag")
            
            if '</svg>' not in content:
                result.warnings.append("icon.svg should end with </svg> tag")
            
            # Check file size (recommend under 10KB for icons)
            file_size = icon_path.stat().st_size
            if file_size > 10240:  # 10KB
                result.warnings.append(f"icon.svg is {file_size} bytes. Consider optimizing for smaller file size.")
                
        except Exception as e:
            result.warnings.append(f"Could not validate icon.svg: {str(e)}")
    
    def _check_recommended_files(self, component_dir: Path, result: ComponentValidationResult):
        """Check for recommended files and suggest improvements"""
        for filename, description in self.recommended_files.items():
            file_path = component_dir / filename
            if not file_path.exists():
                result.suggested_improvements.append(f"Add {filename}: {description}")
    
    async def _validate_component_structure(self, component_dir: Path, result: ComponentValidationResult):
        """Validate overall React Native component structure"""
        try:
            # Check TypeScript files
            ts_files = list(component_dir.glob("**/*.ts")) + list(component_dir.glob("**/*.tsx"))
            if len(ts_files) == 0:
                result.warnings.append("No TypeScript files found besides index.ts")
            elif len(ts_files) > 20:
                result.warnings.append(f"Component has {len(ts_files)} TypeScript files. Consider reducing complexity.")
            
            # Check for common problematic directories
            problematic_dirs = ["node_modules", ".git", "dist", "build", "android", "ios"]
            for dir_name in problematic_dirs:
                if (component_dir / dir_name).exists():
                    result.warnings.append(f"{dir_name} directory found. This should not be included in published components.")
            
            # Check total file count
            total_files = sum(1 for _ in component_dir.rglob('*') if _.is_file())
            if total_files == 0:
                result.issues.append("Component directory is empty")
                result.structure_valid = False
            elif total_files > 100:
                result.warnings.append(f"Component has {total_files} files. Consider reducing complexity.")
            
            # Check for React Native specific files
            rn_specific_files = ["metro.config.js", "babel.config.js"]
            for rn_file in rn_specific_files:
                if (component_dir / rn_file).exists():
                    result.warnings.append(f"{rn_file} found. This is typically not needed for WMX components.")
            
        except Exception as e:
            result.warnings.append(f"Could not fully validate component structure: {str(e)}")
    
    def _is_valid_version(self, version: str) -> bool:
        """Basic semantic version validation"""
        import re
        # Basic semver pattern: major.minor.patch
        pattern = r'^\d+\.\d+\.\d+(?:-[0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*)?(?:\+[0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*)?$'
        return bool(re.match(pattern, version))
    
    def _is_valid_rn_version(self, version: str) -> bool:
        """Validate React Native version format"""
        import re
        # React Native version pattern: >=0.72.0 or ^0.72.0 or ~0.72.0
        pattern = r'^[><=~^]*\d+\.\d+\.\d+$'
        return bool(re.match(pattern, version))
