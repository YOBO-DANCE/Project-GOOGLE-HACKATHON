# -*- coding: utf-8 -*-
"""
Sports Concierge Database Package.

Provides the :class:`DatabaseManager` class for Supabase persistence,
including audit-logging of security events.

Usage::

    from database.manager import db_manager

    db_manager.log_security_event("team_schedule.pdf", "safe", 0, "MIME: application/pdf")
"""

from database.manager import DatabaseManager, db_manager

__all__ = [
    "DatabaseManager",
    "db_manager",
]
