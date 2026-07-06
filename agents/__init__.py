# -*- coding: utf-8 -*-
"""
Sports Concierge Agents Package.

Exposes the Guard Agent (security gate with HITL) and Coach Agent (training
plan generation via Ollama) for use by the Streamlit orchestrator.
"""

from agents.guard import GuardAgent, guard_agent
from agents.coach import CoachAgent, coach_agent

__all__ = [
    "GuardAgent",
    "guard_agent",
    "CoachAgent",
    "coach_agent",
]
