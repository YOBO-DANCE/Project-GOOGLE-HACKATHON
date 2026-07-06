# -*- coding: utf-8 -*-
"""
Sports Concierge Tools Package.

Provides the FastMCP server definition (async tools) and sync helper wrappers
for in-process use by the ADK agents and Streamlit orchestrator.

Exports:
    - ``mcp`` — The FastMCP server instance.
    - ``get_email_context_sync``, ``get_drive_files_sync``, ``scan_file_security_sync``
      — Sync wrappers around the async tool implementations.
    - ``get_email_context``, ``get_drive_files``, ``scan_file_security``
      — The async MCP-decorated tool functions (aliased with ``_mcp`` suffix).
    - ``run_server`` — Backwards-compatible server launcher.
"""

from tools.server_mcp import (
    mcp,
    get_email_context_sync,
    get_drive_files_sync,
    scan_file_security_sync,
    get_email_context as get_email_context_mcp,
    get_drive_files as get_drive_files_mcp,
    scan_file_security as scan_file_security_mcp,
)

# Alias sync wrappers as the primary public API for in-process consumers
get_email_context = get_email_context_sync
get_drive_files = get_drive_files_sync
scan_file_security = scan_file_security_sync

__all__ = [
    "mcp",
    "get_email_context",
    "get_drive_files",
    "scan_file_security",
    "get_email_context_sync",
    "get_drive_files_sync",
    "scan_file_security_sync",
    "get_email_context_mcp",
    "get_drive_files_mcp",
    "scan_file_security_mcp",
]
