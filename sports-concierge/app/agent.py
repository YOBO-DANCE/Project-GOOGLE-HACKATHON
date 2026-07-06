# ruff: noqa
# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
Sports Concierge Agent — Multi-Agent System (Google ADK).

Architecture
------------
This module defines a **multi-agent topology** using Google ADK's ``Agent``
class with specialised tools for security-aware training plan generation:

1. **GuardAgent** — Security gate with Human-in-the-Loop (HITL).
   Evaluates files and user input for threats, produces a proceed / halt
   decision. The Coach Agent **requires** a successful security check
   before generating a plan (enforced via a security token flag).

2. **CoachAgent** — Elite training plan generator.
   Receives a structured JSON payload (goals, level, injury history, schedule,
   email/drive context) and returns a Markdown-formatted plan via Gemini or
   Ollama.

The root ``Agent`` orchestrates the full workflow with ADK tool functions.
Each tool is wrapped as an ADK callable so Gemini can decide which actions
to take and in what order.

Security enforcement
--------------------
The ``_check_security`` tool sets a module-level flag when it determines
input is safe. The ``_generate_training_plan`` tool checks this flag before
proceeding. If the flag is not set (security was skipped), it returns an
error — this enforces the HITL gate even if Gemini tries to skip the
security step.

Deployment
----------
This agent is served by the FastAPI app in ``fast_api_app.py`` and can be
deployed to Vertex AI Agent Engine via ``agents-cli deploy``. A2A protocol
endpoints are attached automatically.
"""

from __future__ import annotations

import json
import os
import sys
from typing import Any

from google.adk.agents import Agent
from google.adk.apps import App
from google.adk.models import Gemini
from google.genai import types

# ---------------------------------------------------------------------------
# Ensure the project root is on sys.path so we can import from agents/,
# tools/, security/, database/ without duplication.
#   Project layout:
#     <project-root>/         ← where agents/, tools/, etc. live
#     <project-root>/sports-concierge/app/agent.py  ← this file
# ---------------------------------------------------------------------------
# From sports-concierge/app/agent.py, the project root is 2 levels up:
#   sports-concierge/app/  ->  sports-concierge/  ->  <project-root>/
_PROJECT_ROOT = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..")
)
# For Vertex AI deployment, the project files are copied into
# sports-concierge/ by scripts/sync-deps.sh. Check that path too.
_ADK_PROJECT_ROOT = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..")
)
for _root in (_PROJECT_ROOT, _ADK_PROJECT_ROOT):
    if _root not in sys.path and os.path.isdir(_root):
        sys.path.insert(0, _root)

from agents.guard import GuardAgent
from agents.coach import CoachAgent
from tools.server_mcp import (
    get_email_context_sync,
    get_drive_files_sync,
    scan_file_security_sync,
)

# ---------------------------------------------------------------------------
# Module-level security token — enforces HITL gate at the code level
# ---------------------------------------------------------------------------
# The _check_security tool sets this dict when it determines content is safe.
# _generate_training_plan checks it before proceeding. If the token is not set
# (meaning Gemini skipped the security step), the coach returns an error.
# This prevents the LLM from bypassing the HITL gate, even if the system
# instruction is ignored.
_security_token: dict[str, Any] | None = None

# ---------------------------------------------------------------------------
# Shared instances
# ---------------------------------------------------------------------------

guard = GuardAgent()
coach = CoachAgent()

# ---------------------------------------------------------------------------
# ADK Tool Functions
# ---------------------------------------------------------------------------
# Each function is registered as an ADK tool. Docstrings and type hints
# are used for JSON Schema generation.


def _gather_email_context(query: str) -> str:
    """Retrieve training-related emails matching a search query.

    Returns email metadata and content (sender, subject, body) that the
    Guard Agent can analyse for phishing or social-engineering attempts.

    Args:
        query: Search term such as "marathon training" or "recovery protocol".
    """
    emails = get_email_context_sync(query)
    return json.dumps(emails, indent=2)


def _gather_drive_files(folder_id: str) -> str:
    """List files in a cloud-drive training folder.

    Returns file metadata (name, MIME type, size, description) for security
    scanning and training plan context.

    Args:
        folder_id: Folder identifier such as "training_2026".
    """
    files = get_drive_files_sync(folder_id)
    return json.dumps(files, indent=2)


def _scan_file(path: str) -> str:
    """Scan a file for security threats before processing.

    Runs MIME-type heuristics and YARA pattern matching. Returns a verdict
    with status (safe/threat/error), score (0-100), and a human-readable
    explanation.

    Args:
        path: Absolute or relative path to the file to scan.
    """
    result = scan_file_security_sync(path)
    return json.dumps(result, indent=2)


def _check_security(user_input: str) -> str:
    """SECURITY GATE: Analyse text content for threats before plan generation.

    This MUST be called BEFORE _generate_training_plan. The Guard Agent
    evaluates user input, emails, and file metadata for injection attacks,
    malicious intent, or policy violations.

    **Enforcement**: After this function runs and determines content is safe,
    it sets an internal security token. The _generate_training_plan function
    will REJECT requests that do not have a valid security token, ensuring
    the HITL gate cannot be bypassed.

    Args:
        user_input: The text content to analyse (sport, level, emails, etc.).
    """
    global _security_token
    decision = guard.process_text(user_input)
    action = decision.get("action", "halt")

    if action == "proceed":
        # Set the security token so generate can proceed
        _security_token = {
            "status": "approved",
            "decision": decision,
        }
    else:
        # Clear any previous token — security was NOT passed
        _security_token = None

    return json.dumps(decision, indent=2)


def _sanitize_text(text: str) -> str:
    """Sanitise user input to remove dangerous patterns before LLM processing.

    Strips shell commands, HTML/script injection, SQL injection, and path
    traversal attempts. Replaces matched patterns with [REDACTED].

    Args:
        text: Raw input string to sanitise.
    """
    return GuardAgent.sanitize_input(text)


def _generate_training_plan(user_context_json: str) -> str:
    """Generate a personalised training plan using the Coach Agent.

    **IMPORTANT**: This tool REQUIRES that _check_security was called first
    and returned a "proceed" verdict. If the security check was skipped or
    failed, this tool returns an error asking the user to run the security
    gate first. This is enforced at the code level, not just the system
    prompt.

    The context should be a JSON string with fields:
      - user_goals: str
      - training_level: str
      - injury_history: str
      - calendar_constraints: str
      - email_context: str
      - drive_files: list

    Returns a Markdown-formatted training plan with daily workouts,
    recovery phases, and progression guidance.

    Args:
        user_context_json: JSON string with athlete profile and goals.
    """
    global _security_token

    # ---- HITL Enforcement: Check security token ---------------------------
    # This is the code-level lock that prevents Gemini from calling the
    # Coach Agent without first passing through the Guard Agent.
    if _security_token is None or _security_token.get("status") != "approved":
        return json.dumps({
            "error": "SECURITY GATE NOT PASSED",
            "message": (
                "The security gate has not been passed. "
                "Please call _check_security first with the user's input "
                "to analyse for threats. If the analysis returns a 'proceed' "
                "verdict, you may then call _generate_training_plan."
            ),
        }, indent=2)

    # ---- Generate the plan -----------------------------------------------
    plan = coach.generate_training_plan(user_context=user_context_json)

    # Clear the security token so each generation requires a fresh check
    _security_token = None

    return plan


# ---------------------------------------------------------------------------
# Root Agent — Sports Concierge
# ---------------------------------------------------------------------------
# System instruction guides Gemini to use the available tools in the proper
# order. The code-level security enforcement in _generate_training_plan acts
# as a backstop to prevent bypassing the HITL gate.

_SPORTS_CONCIERGE_INSTRUCTION = """You are an elite sports concierge agent that helps athletes generate personalised training plans.

## Your Workflow (MANDATORY ORDER)

1. **Gather Context** — Use tools to collect information:
   - `_gather_email_context` — search for relevant training emails
   - `_gather_drive_files` — find training documents in the cloud drive
   - `_scan_file` — scan any retrieved files for security threats

2. **Sanitise & Check Security** (MANDATORY before generation):
   - `_sanitize_text` — sanitise user input before passing to the coach
   - `_check_security` — THIS MUST BE CALLED BEFORE GENERATION
     The _generate_training_plan tool will REFUSE to work without a
     valid security check.

3. **Generate Plan** — Use `_generate_training_plan` with a JSON payload:
   - user_goals (what the athlete wants to achieve)
   - training_level (Beginner / Intermediate / Advanced / Elite)
   - injury_history (past and current injuries or limitations)
   - calendar_constraints (when the athlete can train)
   - email_context (relevant emails from coaches, physios, nutritionists)
   - drive_files (training documents found in the cloud)

## Output Quality
Training plans must be:
- Markdown-formatted with a table (Day | Workout | Intensity | Notes)
- Include recovery phases every 3-4 days
- Reference the athlete's specific goals and injuries
- Progressive overload across weeks
- Authoritative and actionable"""

# Build the root agent with all tools
root_agent = Agent(
    name="sports_concierge",
    model=Gemini(
        model="gemini-2.0-flash",
        retry_options=types.HttpRetryOptions(attempts=3),
    ),
    instruction=_SPORTS_CONCIERGE_INSTRUCTION,
    tools=[
        _gather_email_context,
        _gather_drive_files,
        _scan_file,
        _check_security,
        _sanitize_text,
        _generate_training_plan,
    ],
)

# ---------------------------------------------------------------------------
# ADK App — used by FastAPI server, A2A, and Vertex AI deployment
# ---------------------------------------------------------------------------

app = App(
    root_agent=root_agent,
    name="sports-concierge",
)

# ---------------------------------------------------------------------------
# Re-export for convenience
# ---------------------------------------------------------------------------

__all__ = [
    "root_agent",
    "app",
    "guard",
    "coach",
]
