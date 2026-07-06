# -*- coding: utf-8 -*-
"""
FastMCP server for Sports Concierge tools.

Exposes three async tools via the Model Context Protocol:

- **get_email_context**  — Retrieve training-related emails.
- **get_drive_files**    — List files in a cloud drive folder.
- **scan_file_security** — Scan a file for security threats.

Each tool is decorated with ``@mcp.tool()``, which auto-generates JSON Schema
from Python type hints and docstrings.

Usage (standalone server):
    python tools/server_mcp.py

Usage (in-process — sync helpers):
    from tools.server_mcp import get_email_context_sync
    emails = get_email_context_sync("marathon training")
"""

from __future__ import annotations

import asyncio
from typing import Any

from fastmcp import FastMCP

from security.sandbox import SecurityScanner

# Shared scanner instance — instantiated once so YARA rules compile only once.
_scanner = SecurityScanner()

# ---------------------------------------------------------------------------
# MCP server instance
# ---------------------------------------------------------------------------

mcp = FastMCP("SportsConciergeTools")


# ---------------------------------------------------------------------------
# Tool implementations (async — used by the MCP decorators)
# ---------------------------------------------------------------------------


async def _get_email_context(query: str) -> list[dict[str, str]]:
    """Mock email retrieval — returns training-related emails matching *query*.

    In production, replace this with a real Gmail / Outlook API call.

    Args:
        query: Search term to filter emails (e.g. ``"marathon training"``).

    Returns:
        A list of dictionaries, each with keys ``sender``, ``subject``, and
        ``content``.
    """
    # Simulate async I/O latency
    await asyncio.sleep(0.2)

    mock_emails: list[dict[str, str]] = [
        {
            "sender": "coach@example.com",
            "subject": "Updated Marathon Training Schedule",
            "content": (
                "Please find attached the revised marathon training plan. "
                "We have increased the long-run mileage per your request."
            ),
        },
        {
            "sender": "nutritionist@example.com",
            "subject": "Pre-Race Nutrition Guidelines",
            "content": (
                "Here are the updated meal plans for the week leading up "
                "to the race."
            ),
        },
        {
            "sender": "physio@example.com",
            "subject": "Recovery Protocol — Achilles Tendon",
            "content": (
                "Continue the eccentric heel-drop exercises twice daily. "
                "Ice after every run."
            ),
        },
        {
            "sender": "team_lead@example.com",
            "subject": "Team Practice — Saturday 6 AM",
            "content": (
                "Reminder: group practice at the track this Saturday. "
                "Bring hydration and timing chips."
            ),
        },
    ]

    # Simple client-side filter
    query_lower = query.lower()
    if query_lower:
        filtered = [
            email
            for email in mock_emails
            if query_lower in email["subject"].lower()
            or query_lower in email["content"].lower()
            or query_lower in email["sender"].lower()
        ]
        return filtered if filtered else mock_emails

    return mock_emails


async def _get_drive_files(folder_id: str) -> list[dict[str, Any]]:
    """Mock drive listing — returns file metadata for a given *folder_id*.

    In production, replace this with a real Google Drive / OneDrive API call.

    Args:
        folder_id: The cloud-drive folder identifier to list.

    Returns:
        A list of file metadata dictionaries (name, MIME type, size, etc.).
    """
    # Simulate async I/O latency
    await asyncio.sleep(0.15)

    mock_files: list[dict[str, Any]] = [
        {
            "name": "Marathon_Plan.pdf",
            "mime_type": "application/pdf",
            "size_bytes": 245_760,
            "modified": "2026-07-05T14:30:00Z",
            "description": "Full marathon training schedule (16 weeks)",
        },
        {
            "name": "Drills.docx",
            "mime_type": (
                "application/vnd.openxmlformats-officedocument."
                "wordprocessingml.document"
            ),
            "size_bytes": 51_200,
            "modified": "2026-07-03T09:00:00Z",
            "description": "Speed and agility drill descriptions",
        },
        {
            "name": "Performance_Metrics_Q3.csv",
            "mime_type": "text/csv",
            "size_bytes": 15_360,
            "modified": "2026-07-01T10:00:00Z",
            "description": "Quarterly performance data with splits and HR zones",
        },
        {
            "name": "Stretching_Routine.mp4",
            "mime_type": "video/mp4",
            "size_bytes": 15_728_640,
            "modified": "2026-06-28T16:00:00Z",
            "description": "Guided warm-up and cool-down stretching video",
        },
    ]

    # Simulate folder context (in production, use the folder_id to query the API)
    _ = folder_id  # reserved for future API integration

    return mock_files


async def _scan_file_security(file_path: str) -> dict[str, Any]:
    """Scan a file for security threats using the ``SecurityScanner``.

    Delegates to :class:`security.sandbox.SecurityScanner` which runs MIME
    heuristics + YARA pattern matching under the hood.

    Args:
        file_path: Absolute or relative path to the file to scan.

    Returns:
        A dict with ``status`` (``"safe"`` | ``"threat"`` | ``"error"``),
        ``score`` (0 – 100), and ``reason`` (human-readable explanation).
    """
    # Run the scan in a thread to avoid blocking the asyncio event loop
    # (``python-magic`` and ``yara-python`` are synchronous FFI calls).
    import functools

    loop = asyncio.get_running_loop()
    result = await loop.run_in_executor(
        None, functools.partial(_scanner.scan, file_path)
    )
    return result# ---------------------------------------------------------------------------
# Sync helper wrappers (for in-process use by guard.py and app.py)
# ---------------------------------------------------------------------------


def _run_async(coro):
    """Run a coroutine synchronously, even if an event loop is already running.

    Falls back to a thread-pool executor to avoid ``RuntimeError`` when
    called from within Streamlit's or FastAPI's running event loop.
    """
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        # No loop running — straightforward case
        return asyncio.run(coro)

    # A loop is already running — execute in a separate thread
    import concurrent.futures

    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
        future = pool.submit(asyncio.run, coro)
        return future.result()


def get_email_context_sync(query: str) -> list[dict[str, str]]:
    """Sync wrapper around :func:`_get_email_context`."""
    return _run_async(_get_email_context(query))


def get_drive_files_sync(folder_id: str) -> list[dict[str, Any]]:
    """Sync wrapper around :func:`_get_drive_files`."""
    return _run_async(_get_drive_files(folder_id))


def scan_file_security_sync(file_path: str) -> dict[str, Any]:
    """Sync wrapper around :func:`_scan_file_security`."""
    return _run_async(_scan_file_security(file_path))


# ---------------------------------------------------------------------------
# FastMCP tool decorators (async — exposed to MCP clients)
# ---------------------------------------------------------------------------


@mcp.tool()
async def get_email_context(query: str) -> list[dict[str, str]]:
    """Search for training-related emails matching a query.

    Returns a list of email dictionaries containing 'sender', 'subject',
    and 'content' fields. Use this tool to gather context about training
    programmes, coach instructions, or nutrition plans from the athlete's
    inbox.

    Args:
        query: Search term to filter emails (e.g. "marathon training").
    """
    return await _get_email_context(query)


@mcp.tool()
async def get_drive_files(folder_id: str) -> list[dict[str, Any]]:
    """List files in a cloud-drive training folder.

    Returns file metadata including name, MIME type, size, and last-modified
    timestamp. Use this tool to discover training documents, performance
    data, and instructional videos.

    Args:
        folder_id: The cloud-drive folder identifier (e.g. "training_2026").
    """
    return await _get_drive_files(folder_id)


@mcp.tool()
async def scan_file_security(file_path: str) -> dict[str, Any]:
    """Scan a file for security threats before processing.

    Returns a dict with 'status' ("safe" or "threat") and 'score' (0–100).
    Use this tool to vet files retrieved from emails or cloud drives before
    the Guard Agent analyses them.

    Args:
        file_path: Full path to the file to scan.
    """
    return await _scan_file_security(file_path)


# ---------------------------------------------------------------------------
# Entrypoint
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print("🏆 Sports Concierge MCP Server running …")
    mcp.run()
