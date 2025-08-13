"""
WaveMaker WMX Component MCP Server
"""
import asyncio
import logging
from typing import List, Optional, Any, Dict
from pathlib import Path
import json

from fastmcp import FastMCP

from api_client import WaveMakerAPIClient  
from git_manager import GitManager
from models import ComponentSearchParams, WMXComponent, ComponentInstallResult
from config import settings
from component_validator import ComponentValidator
from publisher import ComponentPublisher

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
async def prepare_wmx_component_installation(
    component_id: str,
    target_path: Optional[str] = None
) -> Dict[str, Any]:
    """
    Prepare WMX component installation by downloading and analyzing files
    Returns installation plan for IDE to execute
    
    Args:
        component_id: Unique identifier of the component to install
        target_path: Custom installation path (defaults to src/main/webapp/components)
        
    Returns:
        Dictionary containing installation plan and file contents
    """
    try:
        logger.info(f"Preparing installation for component: {component_id}")
        
        # Get component details
        async with WaveMakerAPIClient() as client:
            component = await client.get_component_details(component_id)
        
        if not component:
            return {
                "success": False,
                "error": f"Component with ID '{component_id}' not found"
            }
        
        # Clone to temporary directory and analyze
        git_manager = GitManager()
        temp_dir = await git_manager.prepare_component(component)
        
        # Read all component files and return their contents
        install_plan = {
            "success": True,
            "component": {
                "id": component.id,
                "name": component.name,
                "version": component.version,
                "description": component.description
            },
            "target_path": target_path or settings.component_base_path,
            "files_to_create": [],
            "instructions": f"""
To install the {component.name} component:

1. Create the directory: {target_path or settings.component_base_path}/{component.name}/
2. Create the following files with the provided content:
""",
            "git_info": {
                "url": str(component.git_url),
                "branch": component.git_branch,
                "commit_hash": "latest"
            }
        }
        
        # Read all files from the temporary directory
        for file_info in git_manager.get_component_files(temp_dir):
            install_plan["files_to_create"].append({
                "path": f"{component.name}/{file_info['relative_path']}",
                "content": file_info["content"],
                "description": f"Component file: {file_info['relative_path']}"
            })
        
        # Add metadata file
        from datetime import datetime
        metadata_content = json.dumps({
            "id": component.id,
            "name": component.name,
            "version": component.version,
            "installed_at": datetime.now().isoformat(),
            "source_url": str(component.git_url),
            "description": component.description,
            "author": component.author.dict()
        }, indent=2)
        
        install_plan["files_to_create"].append({
            "path": f"{component.name}/.wmx-component-metadata.json",
            "content": metadata_content,
            "description": "Component metadata file"
        })
        
        # Cleanup temp directory
        git_manager.cleanup_temp(temp_dir)
        
        return install_plan
        
    except Exception as e:
        logger.error(f"Error preparing component installation: {e}")
        return {
            "success": False,
            "error": str(e)
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


@mcp.tool()
async def validate_wmx_component(
    component_path: str,
    strict_validation: bool = True
) -> Dict[str, Any]:
    """
    Validate a local WMX component for marketplace publishing
    
    Args:
        component_path: Path to the local component directory
        strict_validation: Whether to enforce strict marketplace requirements
        
    Returns:
        Dictionary containing validation results and requirements
    """
    try:
        validator = ComponentValidator()
        validation_result = await validator.validate_component(component_path, strict_validation)
        
        return {
            "valid": validation_result.valid,
            "component_name": validation_result.component_name,
            "component_path": validation_result.component_path,
            "issues": validation_result.issues,
            "warnings": validation_result.warnings,
            "requirements_met": validation_result.requirements_met,
            "suggested_improvements": validation_result.suggested_improvements,
            "marketplace_ready": validation_result.marketplace_ready,
            "structure_valid": validation_result.structure_valid,
            "metadata": validation_result.metadata
        }
        
    except Exception as e:
        logger.error(f"Error validating component: {e}")
        return {
            "valid": False,
            "error": str(e),
            "marketplace_ready": False
        }

@mcp.tool()
async def prepare_component_for_publishing(
    component_path: str,
    git_repo_name: Optional[str] = None,
    marketplace_category: Optional[str] = None,
    tags: Optional[List[str]] = None,
    author_name: Optional[str] = None,
    author_email: Optional[str] = None,
    author_organization: Optional[str] = None
) -> Dict[str, Any]:
    """
    Prepare a local WMX component for marketplace publishing
    
    Args:
        component_path: Path to the local component directory
        git_repo_name: Desired Git repository name (defaults to component name)
        marketplace_category: Component category for marketplace
        tags: List of tags for component discovery
        author_name: Author name
        author_email: Author email
        author_organization: Author organization
        
    Returns:
        Dictionary containing publishing preparation details
    """
    try:
        publisher = ComponentPublisher()
        
        # Prepare author info if provided
        author_info = None
        if author_name or author_email or author_organization:
            author_info = {
                "name": author_name or "Unknown",
                "email": author_email or "",
                "organization": author_organization or ""
            }
        
        prep_result = await publisher.prepare_component_for_publishing(
            component_path=component_path,
            git_repo_name=git_repo_name,
            marketplace_category=marketplace_category,
            tags=tags,
            author_info=author_info
        )
        
        return prep_result.dict()
        
    except Exception as e:
        logger.error(f"Error preparing component for publishing: {e}")
        return {
            "success": False,
            "error": str(e)
        }

@mcp.tool()
async def publish_wmx_component_dry_run(
    component_path: str,
    git_repo_name: Optional[str] = None,
    marketplace_category: Optional[str] = None,
    tags: Optional[List[str]] = None,
    author_name: Optional[str] = None,
    author_email: Optional[str] = None,
    author_organization: Optional[str] = None
) -> Dict[str, Any]:
    """
    Simulate publishing a WMX component to marketplace (dry run)
    
    Args:
        component_path: Path to the local component directory
        git_repo_name: Desired Git repository name
        marketplace_category: Component category for marketplace
        tags: List of tags for component discovery
        author_name: Author name
        author_email: Author email  
        author_organization: Author organization
        
    Returns:
        Dictionary containing simulation result
    """
    try:
        publisher = ComponentPublisher()
        
        # Prepare author info if provided
        author_info = None
        if author_name or author_email or author_organization:
            author_info = {
                "name": author_name or "Unknown", 
                "email": author_email or "",
                "organization": author_organization or ""
            }
        
        marketplace_config = {
            "api_key": settings.api_key,
            "base_url": settings.api_base_url
        }
        
        result = await publisher.simulate_component_publishing(
            component_path=component_path,
            marketplace_config=marketplace_config,
            git_repo_name=git_repo_name,
            marketplace_category=marketplace_category,
            tags=tags,
            author_info=author_info
        )
        
        return result.dict()
        
    except Exception as e:
        logger.error(f"Error in component publishing dry run: {e}")
        return {
            "success": False,
            "error": str(e),
            "step": "dry_run"
        }

# @mcp.tool() 
# async def get_component_publishing_template() -> Dict[str, Any]:
#     """
#     Get a template structure for creating new WMX components
    
#     Returns:
#         Dictionary containing component template structure and files
#     """
#     try:
#         template_structure = {
#             "wmconfig_json": {
#                 "name": "MyComponent",
#                 "displayName": "My Custom Component", 
#                 "version": "1.0.0",
#                 "description": "A custom WMX component",
#                 "category": "Custom",
#                 "type": "widget",
#                 "author": "Your Name",
#                 "license": "MIT",
#                 "tags": ["custom", "utility"],
#                 "wavemakerVersion": ">=11.0.0",
#                 "dependencies": [],
#                 "properties": {
#                     "value": {
#                         "type": "string",
#                         "bindable": "in-bound",
#                         "default": ""
#                     },
#                     "onChange": {
#                         "type": "event",
#                         "parameters": [
#                             {"name": "newValue", "type": "string"}
#                         ]
#                     }
#                 }
#             },
#             "index_ts_template": '''import { Component, OnInit, Input, Output, EventEmitter } from '@angular/core';

# @Component({
#     selector: 'my-component',
#     template: `
#         <div class="my-component">
#             <button (click)="handleClick()" 
#                     [disabled]="disabled">
#                 {{ displayText || 'Click Me' }}
#             </button>
#         </div>
#     `,
#     styles: [`
#         .my-component {
#             display: inline-block;
#         }
        
#         .my-component button {
#             padding: 8px 16px;
#             border: 1px solid #ccc;
#             border-radius: 4px;
#             background: #fff;
#             cursor: pointer;
#         }
        
#         .my-component button:hover {
#             background: #f5f5f5;
#         }
        
#         .my-component button:disabled {
#             opacity: 0.6;
#             cursor: not-allowed;
#         }
#     `]
# })
# export class MyComponent implements OnInit {
#     @Input() value: string = '';
#     @Input() displayText: string = 'Click Me';
#     @Input() disabled: boolean = false;
    
#     @Output() onChange = new EventEmitter<string>();
    
#     ngOnInit() {
#         console.log('MyComponent initialized with value:', this.value);
#     }
    
#     handleClick() {
#         if (!this.disabled) {
#             const newValue = this.value + '_clicked';
#             this.onChange.emit(newValue);
#         }
#     }
# }

# // Register the component with WaveMaker
# export { MyComponent };
# ''',
#             "icon_svg_template": '''<svg width="24" height="24" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
#     <rect x="3" y="3" width="18" height="18" rx="2" stroke="#333" stroke-width="2" fill="#f8f9fa"/>
#     <path d="M9 12l2 2 4-4" stroke="#333" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
# </svg>''',
#             "readme_template": '''# MyComponent

# A custom WMX component for WaveMaker applications.

# ## Description

# Brief description of what this component does.

# ## Usage

# Add the component to your WaveMaker page and configure its properties:

# - **value**: Input value for the component
# - **displayText**: Text to display on the button
# - **disabled**: Whether the component is disabled
# - **onChange**: Event triggered when component value changes

# ## Properties

# ### Inputs
# - `value` (string): The current value of the component
# - `displayText` (string): Text displayed on the button
# - `disabled` (boolean): Disables user interaction

# ### Outputs  
# - `onChange`: Emitted when the component value changes

# ## Installation

# This component can be installed through the WaveMaker marketplace.

# ## Development

# The component is built using Angular and follows WMX component conventions:
# - `index.ts`: Main component implementation
# - `wmconfig.json`: Component configuration and metadata
# - `icon.svg`: Component icon for the palette

# ## License

# MIT License
# ''',
#             "files_to_create": [
#                 {
#                     "path": "wmconfig.json",
#                     "content_key": "wmconfig_json",
#                     "description": "WMX component configuration file"
#                 },
#                 {
#                     "path": "index.ts", 
#                     "content_key": "index_ts_template",
#                     "description": "Component entry file and implementation"
#                 },
#                 {
#                     "path": "icon.svg",
#                     "content_key": "icon_svg_template",
#                     "description": "Component icon (SVG format)"
#                 },
#                 {
#                     "path": "README.md",
#                     "content_key": "readme_template", 
#                     "description": "Component documentation"
#                 }
#             ],
#             "recommended_files": [
#                 "CHANGELOG.md - Version history",
#                 "LICENSE - License file",
#                 "demo.html - Component demo page",
#                 "package.json - NPM dependencies (if needed)"
#             ]
#         }
        
#         return {
#             "success": True,
#             "template": template_structure,
#             "instructions": [
#                 "1. Create a new directory for your WMX component",
#                 "2. Create the required files: index.ts, wmconfig.json, icon.svg",
#                 "3. Customize wmconfig.json with your component details",
#                 "4. Implement your component logic in index.ts using Angular",
#                 "5. Design your component icon in icon.svg",
#                 "6. Add documentation in README.md",
#                 "7. Use validate_wmx_component to check if ready for publishing"
#             ]
#         }
        
#     except Exception as e:
#         logger.error(f"Error getting component template: {e}")
#         return {
#             "success": False,
#             "error": str(e)
#         }

@mcp.tool() 
async def get_component_publishing_template() -> Dict[str, Any]:
    """
    Get a template structure for creating new WMX React Native components
    
    Returns:
        Dictionary containing component template structure and files
    """
    try:
        template_structure = {
            "wmconfig_json": {
                "name": "MyComponent",
                "displayName": "My Custom Component", 
                "version": "1.0.0",
                "description": "A custom WMX React Native component",
                "category": "Custom",
                "type": "component",
                "author": "Your Name",
                "license": "MIT",
                "tags": ["custom", "utility", "react-native"],
                "reactNativeVersion": ">=0.72.0",
                "dependencies": [],
                "properties": {
                    "title": {
                        "type": "string",
                        "bindable": "in-bound",
                        "default": "Click Me"
                    },
                    "disabled": {
                        "type": "boolean",
                        "bindable": "in-bound", 
                        "default": False
                    },
                    "onPress": {
                        "type": "event",
                        "parameters": [
                            {"name": "value", "type": "string"}
                        ]
                    }
                }
            },
            "index_ts_template": '''import React from 'react';
import {
  View,
  Text,
  TouchableOpacity,
  StyleSheet,
  ViewStyle,
  TextStyle
} from 'react-native';

interface MyComponentProps {
  title?: string;
  disabled?: boolean;
  onPress?: (value: string) => void;
  style?: ViewStyle;
}

const MyComponent: React.FC<MyComponentProps> = ({
  title = 'Click Me',
  disabled = false,
  onPress,
  style
}) => {
  const handlePress = () => {
    if (!disabled && onPress) {
      onPress(title + ' pressed');
    }
  };

  return (
    <View style={[styles.container, style]}>
      <TouchableOpacity
        style={[
          styles.button,
          disabled && styles.buttonDisabled
        ]}
        onPress={handlePress}
        disabled={disabled}
        activeOpacity={0.7}
      >
        <Text style={[
          styles.buttonText,
          disabled && styles.buttonTextDisabled
        ]}>
          {title}
        </Text>
      </TouchableOpacity>
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    alignItems: 'center',
    justifyContent: 'center',
  },
  button: {
    backgroundColor: '#007AFF',
    paddingHorizontal: 20,
    paddingVertical: 12,
    borderRadius: 8,
    minWidth: 100,
    alignItems: 'center',
    justifyContent: 'center',
  },
  buttonDisabled: {
    backgroundColor: '#CCCCCC',
  },
  buttonText: {
    color: '#FFFFFF',
    fontSize: 16,
    fontWeight: '600',
  },
  buttonTextDisabled: {
    color: '#666666',
  },
});

export default MyComponent;
export { MyComponentProps };
''',
            "types_ts_template": '''export interface MyComponentProps {
  title?: string;
  disabled?: boolean;
  onPress?: (value: string) => void;
  style?: import('react-native').ViewStyle;
}

export interface MyComponentRef {
  focus: () => void;
  blur: () => void;
}
''',
            "icon_svg_template": '''<svg width="24" height="24" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
    <rect x="3" y="5" width="18" height="14" rx="4" stroke="#007AFF" stroke-width="2" fill="#E3F2FD"/>
    <circle cx="12" cy="12" r="3" fill="#007AFF"/>
    <path d="M9 12h6" stroke="white" stroke-width="2" stroke-linecap="round"/>
</svg>''',
            "demo_tsx_template": '''import React, { useState } from 'react';
import { View, Text, StyleSheet, Alert } from 'react-native';
import MyComponent from './index';

const MyComponentDemo: React.FC = () => {
  const [pressCount, setPressCount] = useState(0);

  const handlePress = (value: string) => {
    setPressCount(count => count + 1);
    Alert.alert('Component Pressed', `Value: ${value}\\nPress count: ${pressCount + 1}`);
  };

  return (
    <View style={styles.container}>
      <Text style={styles.title}>MyComponent Demo</Text>
      
      <View style={styles.section}>
        <Text style={styles.sectionTitle}>Default Button</Text>
        <MyComponent 
          title="Default Button"
          onPress={handlePress}
        />
      </View>

      <View style={styles.section}>
        <Text style={styles.sectionTitle}>Custom Title</Text>
        <MyComponent 
          title="Custom Title"
          onPress={handlePress}
        />
      </View>

      <View style={styles.section}>
        <Text style={styles.sectionTitle}>Disabled Button</Text>
        <MyComponent 
          title="Disabled Button"
          disabled={true}
          onPress={handlePress}
        />
      </View>
      
      <Text style={styles.counter}>Total Presses: {pressCount}</Text>
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    padding: 20,
    backgroundColor: '#F5F5F5',
  },
  title: {
    fontSize: 24,
    fontWeight: 'bold',
    textAlign: 'center',
    marginBottom: 30,
    color: '#333',
  },
  section: {
    marginBottom: 30,
    alignItems: 'center',
  },
  sectionTitle: {
    fontSize: 16,
    fontWeight: '600',
    marginBottom: 10,
    color: '#666',
  },
  counter: {
    fontSize: 18,
    textAlign: 'center',
    marginTop: 20,
    color: '#007AFF',
    fontWeight: '600',
  },
});

export default MyComponentDemo;
''',
            "readme_template": '''# MyComponent

A custom WMX React Native component for WaveMaker applications.

## Description

A customizable button component built with React Native that provides consistent styling and behavior across iOS and Android platforms.

## Usage

import MyComponent from './MyComponent';

// Basic usage
<MyComponent
title="Click Me"
onPress={(value) => console.log('Pressed:', value)}
/>

// With custom styling
<MyComponent
title="Custom Button"
disabled={false}
onPress={handlePress}
style={{ marginTop: 20 }}
/>

text

## Properties

### Props
- `title` (string, optional): Text displayed on the button. Default: "Click Me"
- `disabled` (boolean, optional): Whether the button is disabled. Default: false
- `onPress` (function, optional): Callback function called when button is pressed
- `style` (ViewStyle, optional): Custom styling for the component container

### Events  
- `onPress`: Emitted when the button is pressed with the button's title value

## Installation

This component can be installed through the WaveMaker marketplace.

## Development

The component is built using React Native and follows WMX component conventions:
- `index.ts`: Main component implementation
- `wmconfig.json`: Component configuration and metadata
- `icon.svg`: Component icon for the palette
- `types.ts`: TypeScript type definitions
- `demo.tsx`: Component demonstration and usage examples

## React Native Version

This component is compatible with React Native >= 0.72.0

## Dependencies

- react: ^18.0.0
- react-native: ^0.72.0

## License

MIT License
''',
            "files_to_create": [
                {
                    "path": "wmconfig.json",
                    "content_key": "wmconfig_json",
                    "description": "WMX component configuration file"
                },
                {
                    "path": "index.ts", 
                    "content_key": "index_ts_template",
                    "description": "Component entry file (React Native implementation)"
                },
                {
                    "path": "icon.svg",
                    "content_key": "icon_svg_template",
                    "description": "Component icon (SVG format)"
                },
                {
                    "path": "types.ts",
                    "content_key": "types_ts_template",
                    "description": "TypeScript type definitions"
                },
                {
                    "path": "demo.tsx",
                    "content_key": "demo_tsx_template",
                    "description": "Component demo and usage examples"
                },
                {
                    "path": "README.md",
                    "content_key": "readme_template", 
                    "description": "Component documentation"
                }
            ],
            "recommended_files": [
                "CHANGELOG.md - Version history",
                "LICENSE - License file", 
                "package.json - NPM dependencies (if needed)",
                "__tests__/ - Unit tests directory",
                ".eslintrc.js - ESLint configuration for code quality"
            ]
        }
        
        return {
            "success": True,
            "template": template_structure,
            "instructions": [
                "1. Create a new directory for your WMX React Native component",
                "2. Create the required files: index.ts, wmconfig.json, icon.svg",
                "3. Customize wmconfig.json with your component details",
                "4. Implement your component logic in index.ts using React Native",
                "5. Define TypeScript types in types.ts",
                "6. Create demo examples in demo.tsx",
                "7. Design your component icon in icon.svg",
                "8. Add documentation in README.md",
                "9. Use validate_wmx_component to check if ready for publishing"
            ]
        }
        
    except Exception as e:
        logger.error(f"Error getting component template: {e}")
        return {
            "success": False,
            "error": str(e)
        }

if __name__ == "__main__":
    mcp.run()
