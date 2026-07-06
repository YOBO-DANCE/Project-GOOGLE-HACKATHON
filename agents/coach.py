# -*- coding: utf-8 -*-
"""
Coach Agent — Elite training plan generator using Gemini or Ollama.

The ``CoachAgent`` class generates hyper-personalised workout routines by
sending a structured context payload to either:

* **Gemini** (Google AI API) — fast, cloud-hosted, requires ``GEMINI_API_KEY``
  or ``GOOGLE_API_KEY`` env var.
* **Ollama** (local) — private, runs ``llama3.1`` locally.

The provider is auto-detected: Gemini is preferred when an API key is
available; Ollama is used as a fallback.

The system prompt assumes the persona of an **elite athletic coach** and
mandates:

* Output formatted as a **Markdown table** (Day, Workout, Intensity, Notes).
* **Recovery phases** interleaved between training blocks.
* Specific references to the athlete's goals, injury history, and schedule
  constraints provided in the context.

If the context payload is empty or both providers are unreachable, the
agent falls back to a **Standard Baseline Plan** (e.g. a Couch-to-5K
structure) with an explanatory warning.

Business value
--------------
After the Guard Agent verifies that retrieved files are safe, the Coach Agent
creates a **transformative, elite-level training plan** using context
gathered from emails and drive files.  The plan emphasises **injury
prevention** (proper warm-up, cool-down, recovery) and **progressive
overload** (gradual intensity increases) so the athlete trains safely and
effectively.  The structured JSON payload ensures every plan references the
athlete's specific goals, injury history, and schedule.

Modularity
----------
The system prompt is configurable per sport, allowing you to inject different
training philosophies for different disciplines::

    swimming_coach = CoachAgent(
        system_prompt="You are an elite swimming coach. ...",
        llm_provider="gemini",
    )
    weightlifting_coach = CoachAgent(
        system_prompt="You are an elite weightlifting coach. ...",
        llm_provider="ollama",
    )
"""

from __future__ import annotations

import json
import os
from typing import Any

import ollama
from google import genai as genai_sdk
from google.genai import types as genai_types

from agents.guard import GuardAgent

# ---------------------------------------------------------------------------
# Elite system prompt
# ---------------------------------------------------------------------------

_ELITE_SYSTEM_PROMPT: str = (
    "You are an elite-level athletic coach with 20+ years of experience "
    "training professional athletes across multiple sports disciplines. "
    "Your reputation depends on delivering **hyper-personalised, data-driven** "
    "training plans that prevent injury while maximising performance gains.\n\n"

    "## MANDATORY OUTPUT STRUCTURE\n"
    "You MUST return the plan as a **Markdown table** with exactly four columns: "
    "| Day | Workout | Intensity | Notes |. "
    "Each row must be a single day's session. "
    "Do NOT use bullet lists or paragraphs for the workout schedule — use the table.\n\n"

    "Below the table, append a **Recovery & Progressions** section with:\n"
    "- **Recovery Phase** — explicit rest days, active recovery protocols, "
    "sleep targets, and nutrition anchors.\n"
    "- **Progression Plan** — how the athlete should increase load over 4 weeks "
    "(volume, intensity, or frequency).\n"
    "- **Injury Caveats** — specific modifications based on the athlete's "
    "reported injuries or limitations.\n\n"

    "## RULES\n"
    "1. **Reference the athlete's specific goals** from the context — "
    "do NOT generate generic advice. "
    "If the context mentions a marathon, build periodised long runs. "
    "If it mentions Achilles tendinopathy, include eccentric heel-drop protocols.\n"
    "2. **Interleave recovery** — every 3–4 training days MUST be followed by "
    "an active recovery or rest day shown in the table.\n"
    "3. **Warm-up & cool-down** — prescribe exact movements (e.g., "
    "'Leg swings + glute bridges 3\u00d710' not 'stretch').\n"
    "4. **Progressive overload** — show how intensity/volume ramps across weeks.\n"
    "5. **Never output 'consult a professional'** — YOU are the professional. "
    "Give actionable, specific instructions.\n"
    "6. **Tone** — authoritative, precise, motivating. Use second person "
    "('You will run 8\u00d7400 m at 5K pace')."
)

# ---------------------------------------------------------------------------
# Standard baseline plan (fallback when context is empty / all providers down)
# ---------------------------------------------------------------------------

_STANDARD_BASELINE_PLAN: str = (
    "# \U0001f3c3 Standard Baseline Plan: Couch-to-5K\n\n"
    "**\u26a0\ufe0f I didn't find specific injury or schedule data, "
    "so I have provided a standard plan. Please upload your medical history "
    "for a tailored version.**\n\n"
    "This 8-week programme builds you from zero running to a continuous 5 km "
    "using a run/walk progression. Each week adds volume gradually.\n\n"
    "| Day | Workout | Intensity | Notes |\n"
    "|-----|---------|-----------|-------|\n"
    "| Mon | 20 min run/walk (1 min run / 2 min walk) | RPE 3\u20134 | Land softly, "
    "mid-foot strike. |\n"
    "| Tue | Rest or 15 min walk | RPE 2 | Active recovery \u2014 keep moving. |\n"
    "| Wed | 20 min run/walk (2 min run / 2 min walk) | RPE 4 | Focus on "
    "breathing rhythm. |\n"
    "| Thu | Rest | \u2014 | Light stretching (hamstrings, calves). |\n"
    "| Fri | 25 min run/walk (3 min run / 1 min walk) | RPE 4\u20135 | Maintain "
    "relaxed shoulders. |\n"
    "| Sat | Cross-train (cycling / swimming) | RPE 3\u20134 | Low impact. |\n"
    "| Sun | Rest | \u2014 | Foam-roll glutes and quads. |\n\n"
    "### Recovery & Progressions\n"
    "- **Recovery Phase**: Every 4th week is a 'cut-back' week \u2014 reduce volume "
    "by 30 %.\n"
    "- **Progression Plan**: Increase run interval length by 1 min per week. "
    "By week 8 you should sustain 30 min continuous running.\n"
    "- **Injury Caveats**: Without medical history I cannot personalise this. "
    "If you have knee or shin pain, reduce volume by 50 % and ice after runs.\n\n"
    "---\n*To receive a fully personalised plan, please provide your injury history, "
    "target event, and weekly schedule.*"
)


# ---------------------------------------------------------------------------
# CoachAgent class
# ---------------------------------------------------------------------------


class CoachAgent:
    """Generates elite-level training plans via Gemini or Ollama.

    The agent uses an authoritative sports-science system prompt that forces
    Markdown-table output, explicit recovery phases, and references to the
    athlete's specific goals/injuries from the context payload.

    Provider selection (``llm_provider``):

    * ``\"auto\"`` — Try Gemini first (if an API key is set), fall back to
      Ollama on failure.
    * ``\"gemini\"`` — Use Gemini only.  Returns an error message on failure.
    * ``\"ollama\"`` — Use Ollama only.  Returns an error message on failure.

    After a successful generation, ``self.last_provider_used`` records which
    provider was actually called (``\"gemini\"`` or ``\"ollama\"``).

    Args:
        system_prompt: Override the default elite-coaching prompt.
        model: Model name. For Ollama defaults to ``\"llama3.1\"``; for
            Gemini defaults to the ``GEMINI_MODEL`` env var or
            ``\"gemini-2.0-flash\"``.
        llm_provider: One of ``\"auto\"``, ``\"gemini\"``, or ``\"ollama\"``.
    """

    def __init__(
        self,
        system_prompt: str | None = None,
        model: str | None = None,
        llm_provider: str = "auto",
    ) -> None:
        self.system_prompt: str = system_prompt or _ELITE_SYSTEM_PROMPT
        self.llm_provider: str = llm_provider
        self.last_provider_used: str | None = None

        # ---- Resolve model names -------------------------------------------
        self._ollama_model: str = model or os.environ.get(
            "OLLAMA_MODEL", "llama3.2:3b"
        )
        self._gemini_model: str = os.environ.get(
            "GEMINI_MODEL", "gemini-2.0-flash"
        )

        # ---- Initialise Gemini client if an API key is available -----------
        self._gemini_client: genai_sdk.Client | None = None
        api_key: str | None = (
            os.environ.get("GEMINI_API_KEY")
            or os.environ.get("GOOGLE_API_KEY")
        )
        if api_key:
            try:
                self._gemini_client = genai_sdk.Client(api_key=api_key)
            except Exception:
                self._gemini_client = None

        # ---- Cache Ollama availability once at init (not on every render) ---
        self._ollama_available: bool = False
        try:
            ollama.list()
            self._ollama_available = True
        except Exception:
            self._ollama_available = False

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def is_gemini_available(self) -> bool:
        """Return ``True`` if the Gemini client was initialised successfully."""
        return self._gemini_client is not None

    def get_engine_label(self) -> tuple[str, str]:
        """Return ``(engine_name, engine_detail)`` for display purposes.

        Priority:
        1. The provider that was actually used in the last generation
           (``last_provider_used``).
        2. The configured/available provider if no generation has happened.
        3. ``("N/A", "No provider available")`` if nothing is configured.

        Example::

            >>> coach.get_engine_label()
            ("Gemini", "gemini-2.0-flash")
        """
        if self.last_provider_used == "gemini":
            return ("Gemini", self._gemini_model)
        if self.last_provider_used == "ollama":
            return ("Ollama", self._ollama_model)
        # No generation yet — show what's configured/available
        if self._gemini_client is not None:
            return ("Gemini", self._gemini_model)
        if self._ollama_available:
            return ("Ollama", self._ollama_model)
        return ("N/A", "No provider available")

    def generate_training_plan(self, user_context: str) -> str:
        """Generate an elite-level training plan from the context payload.

        The *user_context* should be a **JSON string** containing structured
        fields:

        .. code-block:: json

            {
              "user_goals": "...",
              "training_level": "...",
              "injury_history": "...",
              "calendar_constraints": "...",
              "email_context": "...",
              "drive_files": ["..."]
            }

        If the context is empty or parsing fails, a **Standard Baseline
        Plan** (Couch-to-5K) is returned with a warning that no specific
        data was found.

        Args:
            user_context: A JSON string with the athlete's profile, or
                a free-text string for backwards compatibility.

        Returns:
            A formatted Markdown training plan (elite or baseline), or a
            fallback error message if all providers are unreachable.
        """
        # ---- Attempt to parse as JSON for structured fields ----------------
        parsed: dict[str, Any] | None = None
        is_empty: bool = False

        if user_context and user_context.strip():
            try:
                parsed = json.loads(user_context)
            except (json.JSONDecodeError, TypeError):
                # Backwards compatibility — treat as plain text string
                parsed = {"email_context": user_context}
        else:
            is_empty = True

        # ---- Empty or insufficient context → baseline plan -----------------
        if is_empty or parsed is None or self._context_too_empty(parsed):
            return _STANDARD_BASELINE_PLAN

        # ---- Build the user message ----------------------------------------
        lines: list[str] = []

        if goals := parsed.get("user_goals"):
            goals = GuardAgent.sanitize_input(goals)
            lines.append(f"## Athlete Goals\n{goals}\n")
        if level := parsed.get("training_level"):
            level = GuardAgent.sanitize_input(level)
            lines.append(f"## Training Level\n{level}\n")
        if injuries := parsed.get("injury_history"):
            injuries = GuardAgent.sanitize_input(injuries)
            lines.append(
                f"## Injury History & Limitations\n{injuries}\n"
            )
        if schedule := parsed.get("calendar_constraints"):
            schedule = GuardAgent.sanitize_input(schedule)
            lines.append(f"## Schedule Constraints\n{schedule}\n")
        if email_ctx := parsed.get("email_context"):
            email_ctx = GuardAgent.sanitize_input(email_ctx)
            lines.append(f"## Email / Context\n{email_ctx}\n")
        if drive_files := parsed.get("drive_files"):
            files_str = ", ".join(
                GuardAgent.sanitize_input(str(f)) for f in drive_files
            )
            lines.append(f"## Relevant Documents\n{files_str}\n")

        body: str = "\n".join(lines)

        user_message: str = (
            f"Athlete Profile:\n{body}\n\n"
            "Using the profile above, generate a complete weekly "
            "training plan as a Markdown table with columns: "
            "| Day | Workout | Intensity | Notes |. "
            "Include a Recovery & Progressions section below the table. "
            "Be specific, actionable, and authoritative."
        )

        # ---- Route to provider ---------------------------------------------
        provider: str = self.llm_provider

        # "auto" → try Gemini first if available
        if provider == "auto" and self._gemini_client is not None:
            result = self._generate_with_gemini(user_message)
            if result is not None:
                self.last_provider_used = "gemini"
                return result
            # Gemini failed → fall through to Ollama
            result = self._generate_with_ollama(user_message)
            if result is not None:
                self.last_provider_used = "ollama"
                return result

        elif provider == "gemini":
            result = self._generate_with_gemini(user_message)
            if result is not None:
                self.last_provider_used = "gemini"
                return result
            self.last_provider_used = None
            return (
                "⚠️ Error generating training plan with Gemini.\n\n"
                "Please ensure your GEMINI_API_KEY or GOOGLE_API_KEY is set "
                "correctly in the `.env` file."
            )

        else:  # "ollama" or auto-fallback
            result = self._generate_with_ollama(user_message)
            if result is not None:
                self.last_provider_used = "ollama"
                return result
            self.last_provider_used = None
            return (
                f"⚠️ Error generating training plan with Ollama.\n\n"
                f"Please ensure Ollama is running locally:\n"
                f"1. Install from https://ollama.com\n"
                f"2. Pull the model: `ollama pull {self._ollama_model}`\n"
                f"3. Start the server: `ollama serve`"
            )

        # If we get here, both providers failed
        return (
            "⚠️ No LLM provider is available.\n\n"
            "Please either:\n"
            "1. Set GEMINI_API_KEY or GOOGLE_API_KEY in `.env` (recommended)\n"
            "2. Start Ollama locally: `ollama serve`"
        )

    # ------------------------------------------------------------------
    # Private — Gemini
    # ------------------------------------------------------------------

    def _generate_with_gemini(self, user_message: str) -> str | None:
        """Call Gemini and return the plan text, or ``None`` on failure."""
        if self._gemini_client is None:
            return None
        try:
            response = self._gemini_client.models.generate_content(
                model=self._gemini_model,
                contents=user_message,
                config=genai_types.GenerateContentConfig(
                    system_instruction=self.system_prompt,
                    temperature=0.7,
                    max_output_tokens=4096,
                ),
            )
            return response.text
        except Exception:
            return None

    # ------------------------------------------------------------------
    # Private — Ollama
    # ------------------------------------------------------------------

    def _generate_with_ollama(self, user_message: str) -> str | None:
        """Call Ollama and return the plan text, or ``None`` on failure."""
        try:
            response = ollama.chat(
                model=self._ollama_model,
                messages=[
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": user_message},
                ],
            )
            return response["message"]["content"]
        except Exception:
            return None

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _context_too_empty(parsed: dict[str, Any]) -> bool:
        """Check whether the parsed context has any meaningful data.

        Returns ``True`` if every field is empty / missing, meaning the
        agent should fall back to the baseline plan.
        """
        meaningful_keys = (
            "user_goals",
            "training_level",
            "injury_history",
            "calendar_constraints",
            "email_context",
            "drive_files",
        )
        for key in meaningful_keys:
            val = parsed.get(key)
            if val and (isinstance(val, str) and val.strip()):
                return False
            if val and isinstance(val, list) and len(val) > 0:
                return False
        return True


# ---------------------------------------------------------------------------
# Module-level singleton for convenience imports
# ---------------------------------------------------------------------------

coach_agent = CoachAgent()
