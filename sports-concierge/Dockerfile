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

# =============================================================================
# Sports Concierge Agent — Google ADK FastAPI Server
# =============================================================================
# Serves the sports concierge multi-agent system with:
#   - Gemini-powered athletic training plan generation
#   - Guard Agent security analysis with HITL
#   - MCP tools (email, drive, file scan)
#   - A2A protocol support for agent-to-agent communication
#   - Vertex AI Agent Engine deployment readiness
#
# This Dockerfile supports TWO build modes:
#
#   1. Manual build (from project root):
#        docker build -t sports-concierge-adk -f sports-concierge/Dockerfile .
#
#   2. Vertex AI deployment (via agents-cli):
#        ./scripts/sync-deps.sh      # copy deps INTO sports-concierge/
#        cd sports-concierge
#        agents-cli deploy           # builds from sports-concierge/ context
#
# For mode 2, the sync-deps.sh script copies agents/, tools/, security/, and
# database/ into sports-concierge/ so the build context is self-contained.
# =============================================================================

FROM python:3.12-slim

# Install system deps for python-magic (libmagic) and yara-python
RUN apt-get update && apt-get install -y --no-install-recommends \
    libmagic1 \
    libmagic-dev \
    build-essential \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Install uv (fast Python package installer)
RUN pip install --no-cache-dir uv==0.8.13

WORKDIR /code

# ============================================================================
# NOTE: This Dockerfile expects the build context to be the PROJECT ROOT.
# All COPY paths below are relative to the project root, NOT to this file.
#
# Build:  docker build -t sports-concierge-adk -f sports-concierge/Dockerfile .
# ============================================================================

# Copy sports-concierge project files (ADK app)
COPY sports-concierge/pyproject.toml sports-concierge/README.md sports-concierge/uv.lock* ./
COPY sports-concierge/app ./app

# Install dependencies via uv
RUN uv sync --frozen

ARG COMMIT_SHA=""
ENV COMMIT_SHA=${COMMIT_SHA}

ARG AGENT_VERSION=0.0.0
ENV AGENT_VERSION=${AGENT_VERSION}

# Create non-root user
RUN useradd -m -s /bin/bash appuser

# Copy shared modules from the project root
# (agent.py uses sys.path to find these at import time)
COPY agents /code/agents
COPY tools /code/tools
COPY security /code/security
COPY database /code/database
COPY requirements.txt /code/requirements-root.txt

# Ensure proper ownership
RUN chown -R appuser:appuser /code
USER appuser

EXPOSE 8080

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=15s \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8080/health')" || exit 1

# Start the FastAPI server (uvicorn)
CMD ["uv", "run", "uvicorn", "app.fast_api_app:app", "--host", "0.0.0.0", "--port", "8080"]
