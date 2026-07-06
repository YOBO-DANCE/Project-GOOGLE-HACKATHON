# -*- coding: utf-8 -*-
"""
Sports Concierge Security Package.

Provides the :class:`SecurityScanner` class for file scanning and security
analysis using YARA pattern matching and MIME-type heuristics.

Usage::

    from security.sandbox import SecurityScanner

    scanner = SecurityScanner()
    result = scanner.scan("team_schedule.pdf")
"""

from security.sandbox import SecurityScanner

__all__ = [
    "SecurityScanner",
]
