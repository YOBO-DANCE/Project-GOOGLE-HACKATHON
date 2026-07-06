# -*- coding: utf-8 -*-
"""
Guard Agent — Security gate with Human-in-the-Loop (HITL) logic.

The ``GuardAgent`` class evaluates files before they reach the Coach Agent.
It delegates file scanning to the ``SecurityScanner`` (via the MCP tool layer)
and decides whether to **proceed** or **halt** based on the result.

Business value
--------------
In a business-grade agent pipeline, an automated security gate prevents
malicious or unexpected files from reaching downstream processing —
especially important when the agent retrieves attachments from emails or
cloud drives before generating a training plan.

HITL flow
---------
::

    process_input("team_schedule.pdf")
        │
        ├─  scan_file_security_sync(file_path)
        │       └─ SecurityScanner.scan()
        │             ├─ MIME heuristics
        │             ├─ YARA pattern matching
        │             └─ {"status", "score", "reason"}
        │
        ├─  status == "safe"   → {"action": "proceed", "data": ...}
        └─  status == "threat" → {"action": "halt", "reason": ..., "score": ...}

The class is designed to be wrapped by a Google ADK ``Agent`` for full LLM
reasoning, or used directly as a plain Python gate (as in the Streamlit
dashboard).
"""

from __future__ import annotations

import re
from typing import Any

from tools.server_mcp import scan_file_security_sync

# ---------------------------------------------------------------------------
# Text-based threat detection — YARA-inspired keyword scoring for user input
# ---------------------------------------------------------------------------

# Keywords that indicate potentially malicious intent when found in user input
# that should not normally contain them.  Scored additively; >= 50 → halt.
_THREAT_KEYWORDS: list[tuple[re.Pattern[str], int]] = [
    (re.compile(r"\b(?:rm|del|format|mkfs)\b", re.IGNORECASE), 30),
    (re.compile(r"\b(?:sudo|su|runas|chmod|chown)\b", re.IGNORECASE), 20),
    (re.compile(r"\b(?:wget|curl|Invoke-WebRequest)\b", re.IGNORECASE), 25),
    (re.compile(r"\b(?:bash|sh|cmd|powershell|python|perl|ruby)\b", re.IGNORECASE), 15),
    (re.compile(r"\b(?:DROP\s+TABLE|DELETE\s+FROM|TRUNCATE)\b", re.IGNORECASE), 40),
    (re.compile(r"\b(?:<script|javascript:|onload|onerror)\b", re.IGNORECASE), 40),
    (re.compile(r"\b(?:/etc/passwd|/etc/shadow|C:\\Windows)", re.IGNORECASE), 40),
    (re.compile(r"\b(?:eval|exec|base64_decode|os\.system)\b", re.IGNORECASE), 35),
]


# ---------------------------------------------------------------------------
# Constants — Strict Mode patterns
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# Strict Mode patterns — comprehensive, case-insensitive, evasion-resistant
# ---------------------------------------------------------------------------
# Patterns are stripped from LLM-bound input to prevent prompt injection,
# shell-command injection, and XSS via crafted file names or context strings.
#
# Each pattern uses IGNORECASE + DOTALL where applicable to catch obfuscated
# variants.  Input is **normalised** before matching to collapse whitespace
# and strip null bytes, making evasion harder.
# ---------------------------------------------------------------------------

_DANGEROUS_PATTERNS: list[re.Pattern[str]] = [
    # ---- Shell command injection ----
    re.compile(r"[;|&`$\x00]\s*(?:bash|sh|cmd|powershell|python|perl|ruby)\b", re.IGNORECASE),
    re.compile(r"\b(?:rm|del|format|mkfs|dd|shutdown|reboot|wget|curl)\s+(?:-rf|/s|/q|--no-check-certificate)\b", re.IGNORECASE),
    re.compile(r"\b(?:(?:sudo|su|runas)\s+)?(?:rm\s+-[rf]|del\s+/[fsq]|format\s+[a-z]:)", re.IGNORECASE),
    re.compile(r"(?:subprocess\.(?:call|popen|run)|os\.system|os\.popen|exec\s*[(（]|eval\s*[(（]|__import__\s*[(（])", re.IGNORECASE),
    # --- Also catch whitespace-padded variants: eval ( "..." )
    re.compile(r"\b(eval|exec)\s+[\(（]?", re.IGNORECASE),
    # ---- HTML / script injection ----
    re.compile(r"<[\s/]*(?:script|iframe|object|embed|form|input|style|link)\b[^>]*>", re.IGNORECASE | re.DOTALL),
    re.compile(r"<[\s/]*script\b[^>]*>.*?<[\s/]*script\s*>", re.IGNORECASE | re.DOTALL),
    re.compile(r"javascript:\s*(?:void\s*\(?0\)?|alert|confirm|prompt)\b", re.IGNORECASE),
    re.compile(r"j\s*a\s*v\s*a\s*s\s*c\s*r\s*i\s*p\s*t\s*:", re.IGNORECASE),  # obfuscated javascript:
    re.compile(r"on(?:load|error|click|mouseover|submit|focus|blur|change|dblclick|keydown|keyup)\s*=", re.IGNORECASE),
    # ---- SQL injection (defence in depth) ----
    re.compile(r"\b(?:DROP|DELETE|TRUNCATE|ALTER|EXEC|EXECUTE)\s+TABLE", re.IGNORECASE),
    re.compile(r"\bUNION\s+(?:ALL\s+)?SELECT\b", re.IGNORECASE),
    re.compile(r"\b(?:OR|AND)\s+1\s*=\s*1\b", re.IGNORECASE),
    # ---- Path traversal ----
    re.compile(r"\.\.(?:\\|/|%2f|%5c)", re.IGNORECASE),
    re.compile(r"\b(?:/etc/passwd|/etc/shadow|C:\\Windows\\System32|/proc/self/environ)", re.IGNORECASE),
    # ---- Prompt injection attempts ----
    re.compile(r"\b(?:ignore|disregard|forget|override)\s+(?:all\s+)?(?:previous|above|instructions|prompts|system|commands)\b", re.IGNORECASE),
    re.compile(r"\byou\s+(?:must|will|shall|have\s+to)\s+(?:ignore|forget|disregard)\b", re.IGNORECASE),
    re.compile(r"\bnew\s+instructions?\s*:\s*", re.IGNORECASE),
]


# ---------------------------------------------------------------------------
# GuardAgent class
# ---------------------------------------------------------------------------


class GuardAgent:
    """Security gate that scans a file and returns a proceed / halt decision.

    The agent holds a ``system_prompt`` so it can be integrated into an ADK
    ``Agent`` definition later, while remaining usable as a plain Python class
    today.

    Args:
        system_prompt: Optional system instruction for ADK integration.
            Defaults to a security-focused prompt.
    """

    def __init__(
        self,
        system_prompt: str | None = None,
    ) -> None:
        self.system_prompt: str = (
            system_prompt
            or (
                "You are a security guard responsible for protecting the user. "
                "Your goal is to analyse file scan results and decide whether "
                "it is safe to proceed. If the file is a threat, you must halt "
                "and never allow unsafe content to pass through."
            )
        )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    @staticmethod
    def _normalise(text: str) -> str:
        """Normalise input to reduce evasion opportunities before matching.

        - Collapses multiple whitespace characters into a single space.
        - Strips null bytes.
        - Normalises Unicode fullwidth parentheses to ASCII.
        """
        text = re.sub(r"\x00+", "", text)
        text = re.sub(r"[\uFF08\uFF09]", lambda m: "(" if m.group(0) == "\uFF08" else ")", text)
        return re.sub(r"\s+", " ", text)

    @staticmethod
    def sanitize_input(text: str, replacement: str = "[REDACTED]") -> str:
        """Strip or neutralise dangerous content from a string before it is
        passed to an LLM or logged.

        **Strict Mode** — normalises the input first (null-byte removal,
        whitespace collapsing, Unicode normalisation), then removes:

        - Shell-command injection patterns (``rm -rf``, ``subprocess.call``, etc.)
        - HTML/script injection (``<script>``, event handlers, ``javascript:``)
        - Prompt injection attempts (``ignore previous instructions``)
        - SQL injection patterns (``DROP TABLE``, ``UNION SELECT``)
        - Path-traversal attempts (``../``, ``/etc/passwd``)

        Each matched pattern is replaced with a safe placeholder
        (default ``[REDACTED]``) so the original structure of the text
        is preserved for auditing purposes.

        Args:
            text: The raw string to sanitise.
            replacement: Placeholder inserted in place of matched patterns.

        Returns:
            The sanitised string with all dangerous patterns replaced.

        Example::

            >>> GuardAgent.sanitize_input(
            ...     "run: rm -rf / && <script>alert(1)</script>"
            ... )
            'run: [REDACTED] && [REDACTED]'
        """
        if not text or not isinstance(text, str):
            return text or ""

        # Normalise first to reduce evasion opportunities
        result: str = GuardAgent._normalise(text)
        for pattern in _DANGEROUS_PATTERNS:
            result = pattern.sub(replacement, result)
        return result

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def process_text(self, user_input: str) -> dict[str, Any]:
        """Analyse **text content** (user input, emails, file names) for
        security threats and return a proceed / halt decision.

        This is the primary entry point for the Streamlit dashboard. Instead
        of scanning a static file path, it evaluates the *actual user content*
        that will be passed to the Coach Agent, using keyword scoring.

        Args:
            user_input: The aggregated text content to analyse.

        Returns:
            A decision dict with the same shape as :meth:`process_input`:

            **Proceed** — content appears safe::

                {"action": "proceed", "data": {"status": "safe", "score": 0, ...}}

            **Halt** — content contains suspicious patterns::

                {"action": "halt", "reason": "…", "score": 60}
        """
        if not user_input or not isinstance(user_input, str):
            return {
                "action": "proceed",
                "data": {"status": "safe", "score": 0, "reason": "No input to scan."},
            }

        normalised: str = GuardAgent._normalise(user_input)
        score: int = 0
        reasons: list[str] = []

        for pattern, weight in _THREAT_KEYWORDS:
            if pattern.search(normalised):
                score += weight
                reasons.append(f"Matched: {pattern.pattern[:50]}")

        reason_text: str = "; ".join(reasons) if reasons else "No suspicious patterns detected."

        if score >= 50:
            return {
                "action": "halt",
                "reason": f"Suspicious content detected (score={score}): {reason_text}",
                "score": min(score, 100),
            }

        return {
            "action": "proceed",
            "data": {
                "status": "safe",
                "score": score,
                "reason": reason_text,
            },
        }

    def process_input(self, file_path: str) -> dict[str, Any]:
        """Scan *file_path* and return a proceed / halt decision.

        This is the original file-scan entry point. It calls the MCP tool's
        sync wrapper, which in turn delegates to
        :class:`security.sandbox.SecurityScanner`.

        Args:
            file_path: Absolute or relative path to the file to evaluate.

        Returns:
            A decision dict:

            **Proceed** — the file is safe::

                {"action": "proceed", "data": {"status": "safe", "score": 0, ...}}

            **Halt** — the file is a threat or an error occurred::

                {"action": "halt", "reason": "…", "score": 100}
        """
        try:
            scan_result: dict[str, Any] = scan_file_security_sync(file_path)
        except Exception as exc:
            # Fail closed — any unexpected error means halt
            return {
                "action": "halt",
                "reason": f"Security scanner failed: {exc}",
                "score": 100,
            }

        status: str = scan_result.get("status", "error")

        if status == "safe":
            return {
                "action": "proceed",
                "data": scan_result,
            }

        # status is "threat" or "error" — halt
        return {
            "action": "halt",
            "reason": scan_result.get(
                "reason", f"File scan returned status: {status}"
            ),
            "score": scan_result.get("score", 100),
        }


# ---------------------------------------------------------------------------
# Module-level singleton for convenience imports
# ---------------------------------------------------------------------------

guard_agent = GuardAgent()
