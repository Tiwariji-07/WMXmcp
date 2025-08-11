"""
WaveMaker WMX Component MCP Server

A Model Context Protocol server for integrating WaveMaker marketplace
components with AI development environments like Cursor IDE.
"""

__version__ = "1.0.0"
__author__ = "Your Name"
__email__ = "your.email@example.com"

from .server import mcp
from .models import WMXComponent, ComponentSearchParams, ComponentInstallResult
from .config import settings

__all__ = [
    "mcp",
    "WMXComponent",
    "ComponentSearchParams", 
    "ComponentInstallResult",
    "settings"
]
