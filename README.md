# WaveMaker WMX Component MCP Server

A Model Context Protocol (MCP) server that enables AI agents like Cursor IDE to search, discover, and install WaveMaker WMX components from the marketplace directly into your WaveMaker projects.

## Features

- **Component Search**: Find WMX components by name, category, tags, or description
- **Detailed Information**: Get comprehensive component details including versions, dependencies, and ratings
- **Automatic Installation**: Clone and install components from Git repositories
- **Project Integration**: Automatically place components in the correct WaveMaker project structure
- **Metadata Tracking**: Keep track of installed components with metadata files

## Installation

```bash
pip install -e .
```


## Configuration

Create a `.env` file based on `.env.example`:
```bash
cp .env.example .env
```


Edit the `.env` file with your WaveMaker API credentials and preferences.

## Usage

### As MCP Server

Start the server for use with Cursor IDE or other MCP clients:
```bash
wavemaker-wmx-mcp
```


### Available Tools

The server exposes these tools to AI agents:

1. **search_wmx_components**: Search for components in the marketplace
2. **get_component_details**: Get detailed information about a specific component  
3. **install_wmx_component**: Install a component into your WaveMaker project
4. **list_installed_components**: List all installed components
