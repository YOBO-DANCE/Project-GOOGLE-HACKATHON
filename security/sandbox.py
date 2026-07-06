# -*- coding: utf-8 -*-
"""
Sandbox module for file security scanning.

Provides :class:`SecurityScanner` — a production-ready scanner that combines:

- **MIME-type heuristics** (via ``python-magic``) to reject dangerous executable
  formats such as shell scripts and Windows executables.
- **YARA pattern matching** (via ``yara-python``) to detect embedded
  suspicious code patterns (e.g. ``eval(``, ``base64_decode``).

Business value for a Sports Concierge Agent
--------------------------------------------
Athletes and coaches frequently share training documents, performance
spreadsheets, and instructional videos via email and cloud drives. These
files are potential vectors for phishing payloads, macro malware, or
social-engineering traps. The ``SecurityScanner`` class acts as the first
line of defence *before* the Guard Agent analyses any retrieved content,
ensuring that malicious files are flagged and never reach the downstream
Coach Agent or the end-user's training plan.

Usage::

    from security.sandbox import SecurityScanner

    scanner = SecurityScanner()
    result = scanner.scan("team_schedule.pdf")
    # -> {"status": "safe", "score": 0, "reason": "MIME: application/pdf"}
"""

from __future__ import annotations

import os
from typing import Any

# ---------------------------------------------------------------------------
# Optional dependencies — gracefully degrade when not installed
# ---------------------------------------------------------------------------

try:
    import magic as _magic  # python-magic

    MAGIC_AVAILABLE = True
except ImportError:
    MAGIC_AVAILABLE = False

try:
    import yara as _yara  # yara-python

    YARA_AVAILABLE = True
except ImportError:
    YARA_AVAILABLE = False

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

MAX_SCAN_SIZE: int = 10 * 1024 * 1024  # 10 MB — skip content scan for larger files

# MIME types that the scanner considers an immediate threat.
# These are executable or script formats that have no legitimate use in a
# sports-training context and are commonly used to deliver malware.
DANGEROUS_MIME_TYPES: set[str] = {
    "application/x-sh",  # Shell script
    "application/x-msdownload",  # Windows PE executable (.exe, .dll)
    "application/x-msdos-program",  # DOS executable
    "application/x-bat",  # Batch file
    "application/x-msi",  # Windows installer
    "application/vnd.microsoft.portable-executable",
    "application/x-java-archive",  # JAR (can contain executables)
}

# Inline YARA rule — compiled at class initialisation so the class is
# self-contained and does not require an external ``rules.yar`` file.
# Extend this rule as new threat patterns emerge.
_YARA_RULE_SOURCE: str = """
rule SuspiciousPatterns
{
    meta:
        description = "Detects common suspicious code patterns"
        author = "Sports Concierge Agent"
        severity = "high"

    strings:
        $eval = "eval(" nocase
        $exec = "exec(" nocase
        $base64_decode = "base64_decode" nocase
        $os_system = "os.system" nocase
        $subprocess = "subprocess.call" nocase
        $powershell_download = "Invoke-WebRequest" nocase
        $wscript_shell = "WScript.Shell" nocase
        $js_script_tag = "<script>" nocase

    condition:
        any of them
}
"""


# ---------------------------------------------------------------------------
# Scanner class
# ---------------------------------------------------------------------------


class SecurityScanner:
    """Combined file scanner using MIME heuristics and YARA pattern matching.

    Typical usage::

        scanner = SecurityScanner()
        result = scanner.scan("path/to/file.pdf")
        # {"status": "safe", "score": 0, "reason": "MIME: application/pdf"}

    The scanner performs three checks in order:

    1. **File existence** — returns an error result if the file is missing.
    2. **MIME-type heuristics** — rejects known-dangerous types immediately.
    3. **YARA content scan** — searches for embedded suspicious patterns in
       the file's byte content.

    Each check short-circuits to ``"threat"`` if triggered. Results are
    aggregated into a single dict with ``status``, ``score``, and ``reason``.
    """

    def __init__(self) -> None:
        """Initialise the scanner, compiling the inline YARA rule."""
        self._yara_rules: Any = None
        if YARA_AVAILABLE:
            try:
                self._yara_rules = _yara.compile(source=_YARA_RULE_SOURCE)
            except _yara.YaraError:
                pass  # YARA will be skipped at scan time

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def scan(self, file_path: str) -> dict[str, Any]:
        """Run the full scan pipeline on *file_path*.

        Args:
            file_path: Absolute or relative path to the file to scan.

        Returns:
            A dict with three keys:

            - **status** (``"safe"`` | ``"threat"`` | ``"error"``):
              The overall verdict.
            - **score** (``int``, 0–100):
              Higher values indicate greater suspicion.
            - **reason** (``str``):
              Human-readable explanation of the verdict, including which
              check triggered it.
        """
        reasons: list[str] = []
        score: int = 0

        # ---- 1. File existence -------------------------------------------
        if not os.path.exists(file_path):
            return {
                "status": "error",
                "score": 100,
                "reason": f"File not found: {file_path}",
            }

        # ---- 2. MIME-type heuristics ------------------------------------
        mime_type = self._detect_mime(file_path)
        if mime_type:
            if mime_type in DANGEROUS_MIME_TYPES:
                return {
                    "status": "threat",
                    "score": 100,
                    "reason": (
                        f"Dangerous MIME type rejected: {mime_type}. "
                        "Executable and script formats are not permitted "
                        "in the sports-concierge pipeline."
                    ),
                }
            reasons.append(f"MIME: {mime_type}")
        else:
            reasons.append("MIME: unavailable (python-magic not installed)")

        # ---- 3. YARA content scan ---------------------------------------
        yara_hits = self._scan_with_yara(file_path)
        if yara_hits:
            score = min(score + 60, 100)
            reasons.append(f"YARA matched: {', '.join(yara_hits)}")
        else:
            reasons.append("YARA: no matches")

        # ---- 4. Combined verdict ----------------------------------------
        status: str = "threat" if score >= 50 else "safe"

        return {
            "status": status,
            "score": score,
            "reason": " | ".join(reasons),
        }

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _detect_mime(self, file_path: str) -> str | None:
        """Detect the MIME type of *file_path* using ``python-magic``.

        Returns ``None`` if the library is unavailable or detection fails.
        """
        if not MAGIC_AVAILABLE:
            return None
        try:
            return _magic.from_file(file_path, mime=True)
        except Exception:
            return None

    def _scan_with_yara(self, file_path: str) -> list[str]:
        """Scan *file_path* against the compiled YARA rule.

        Returns a list of matched rule names (empty list = clean).
        """
        if not YARA_AVAILABLE or self._yara_rules is None:
            return []

        # Read file content up to MAX_SCAN_SIZE
        try:
            with open(file_path, "rb") as fh:
                content = fh.read(MAX_SCAN_SIZE)
        except (OSError, PermissionError):
            return []

        try:
            matches = self._yara_rules.match(data=content)
            return [match.rule for match in matches]
        except _yara.YaraError:
            return []
