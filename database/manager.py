# -*- coding: utf-8 -*-
"""
Supabase persistence layer for the Sports Concierge Agent.

The :class:`DatabaseManager` class provides a thin wrapper around the
``supabase-py`` client, enabling audit-logging of security events into a
``security_logs`` table.

Audit-logging rationale
-----------------------
For security-focused AI agents, every file-scan decision — whether a file is
allowed (proceed) or rejected (halt) — MUST be recorded in a durable,
queryable store.  This audit trail serves several critical purposes:

* **Accountability** — Prove that the Guard Agent evaluated every file before
  the Coach Agent generated a training plan.
* **Forensics** — When an incident occurs (e.g. a malicious file evades
  detection), the logs show exactly what happened, when, and why.
* **Compliance** — Business-grade systems often require an immutable log of
  security decisions (SOC 2, ISO 27001).
* **Improvement** — Logged scores and reasons can be aggregated to tune YARA
  rules and MIME heuristics over time.

The module is designed to degrade gracefully: if the Supabase project is not
configured or unreachable, the agent continues to work locally and prints a
warning instead of crashing.

Usage::

    from database.manager import db_manager

    db_manager.log_security_event("team_schedule.pdf", "safe", 0, "MIME OK")
"""

from __future__ import annotations

import os
import sys
from typing import Any

from dotenv import load_dotenv

# ---------------------------------------------------------------------------
# Optional dependency — gracefully degrade when supabase-py is not installed
# or when environment variables are missing.
# ---------------------------------------------------------------------------

try:
    from supabase import create_client, Client
except ImportError:
    create_client = None  # type: ignore[assignment]
    Client = None  # type: ignore[assignment,misc]

load_dotenv()

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_TABLE_NAME: str = "security_logs"


# ---------------------------------------------------------------------------
# DatabaseManager class
# ---------------------------------------------------------------------------


class DatabaseManager:
    """Thin wrapper around ``supabase-py`` for security-event audit logging.

    The manager reads ``SUPABASE_URL`` and ``SUPABASE_KEY`` from the
    environment (loaded via ``python-dotenv``) and initialises the Supabase
    client lazily on first use.

    If the dependencies or environment variables are unavailable, the manager
    enters a **degraded mode** where all operations are no-ops with a warning
    printed to stderr.  This ensures the Sports Concierge Agent can be
    developed and tested locally without a connection to Supabase.

    Args:
        url: Supabase project URL.  Falls back to the ``SUPABASE_URL`` env var.
        key: Supabase service-role or anon key.  Falls back to the
            ``SUPABASE_KEY`` env var.
    """

    def __init__(
        self,
        url: str | None = None,
        key: str | None = None,
    ) -> None:
        self._url: str | None = url or os.getenv("SUPABASE_URL")
        self._key: str | None = key or os.getenv("SUPABASE_KEY")
        self._client: Client | None = None
        self._available: bool = False

        self._initialise()

    # ------------------------------------------------------------------
    # Public Properties
    # ------------------------------------------------------------------

    @property
    def is_available(self) -> bool:
        """Whether the Supabase client was successfully initialised."""
        return self._available

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def fetch_recent_logs(self, limit: int = 10) -> list[dict[str, Any]]:
        """Fetch the most recent rows from the ``security_logs`` table.

        Results are ordered by ``created_at`` descending so the newest
        entries appear first.

        Args:
            limit: Maximum number of rows to return (default 10).

        Returns:
            A list of row dicts, or an empty list if the database is
            unavailable or the query fails (degraded mode).
        """
        if not self._available or self._client is None:
            self._warn("Database unavailable — cannot fetch security logs.")
            return []

        try:
            response = (
                self._client.table(_TABLE_NAME)
                .select("*")
                .order("created_at", desc=True)
                .limit(limit)
                .execute()
            )
            if response.data:
                return list(response.data)
            return []
        except Exception as exc:
            self._warn(f"Failed to fetch security logs: {exc}")
            return []

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def log_security_event(
        self,
        file_path: str,
        status: str,
        score: int,
        reason: str,
    ) -> dict[str, Any] | None:
        """Insert a row into the ``security_logs`` table.

        Each row captures the filename, scan status (safe / threat / error),
        numeric score (0–100), and a human-readable reason.  The ``timestamp``
        is set server-side by Supabase's ``now()`` default.

        Args:
            file_path: The path of the file that was scanned.
            status: The verdict — ``\"safe\"``, ``\"threat\"``, or ``\"error\"``.
            score: Numeric suspicion score (0 = benign, 100 = malicious).
            reason: Human-readable explanation from the ``SecurityScanner``.

        Returns:
            The inserted row data as a dict, or ``None`` if the database
            is unavailable (degraded mode).

        Warning:
            Prints a warning to stderr when the database is not configured
            or the insert fails, but **never** raises an exception to the
            caller.
        """
        if not self._available or self._client is None:
            self._warn("Database unavailable — skipping security event log.")
            return None

        row: dict[str, Any] = {
            "filename": os.path.basename(file_path) if file_path else "unknown",
            "status": status,
            "score": score,
            "reason": reason,
        }

        try:
            response = (
                self._client.table(_TABLE_NAME)
                .insert(row)
                .execute()
            )
            if response.data:
                return response.data[0] if isinstance(response.data, list) else response.data
            return None
        except Exception as exc:
            self._warn(f"Failed to log security event: {exc}")
            return None

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _initialise(self) -> None:
        """Attempt to create the Supabase client.

        If ``supabase-py`` is not installed or the environment variables are
        missing, the manager enters degraded mode.
        """
        if create_client is None:
            self._warn(
                "supabase-py is not installed. "
                "Run: pip install supabase"
            )
            return

        if not self._url or not self._key:
            self._warn(
                "SUPABASE_URL and/or SUPABASE_KEY not set in environment. "
                "See .env.example for setup instructions."
            )
            return

        try:
            self._client = create_client(self._url, self._key)
            self._available = True
        except Exception as exc:
            self._warn(f"Failed to initialise Supabase client: {exc}")

    @staticmethod
    def _warn(message: str) -> None:
        """Print a warning to stderr with a ``[db]`` prefix."""
        print(f"[db] WARNING: {message}", file=sys.stderr)


# ---------------------------------------------------------------------------
# Module-level singleton for convenience imports
# ---------------------------------------------------------------------------

db_manager = DatabaseManager()
