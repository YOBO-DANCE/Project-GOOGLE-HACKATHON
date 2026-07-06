# =============================================================================
# Sports Concierge Agent — Streamlit Demo Dockerfile
# =============================================================================
# Build:   docker build -t sports-concierge .
# Run:      docker run -p 8501:8501 sports-concierge
# Compose:  docker compose up
# =============================================================================

FROM python:3.12-slim

WORKDIR /app

# Install system deps needed for python-magic (libmagic) and yara-python
RUN apt-get update && apt-get install -y --no-install-recommends \
    libmagic1 \
    libmagic-dev \
    build-essential \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Copy dependency files first (for Docker layer caching)
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application
COPY agents/ ./agents/
COPY tools/ ./tools/
COPY security/ ./security/
COPY database/ ./database/
COPY app.py .
COPY malicious_test.sh .

# Create a non-root user for security
RUN useradd -m -s /bin/bash appuser && \
    chown -R appuser:appuser /app
USER appuser

# Streamlit port
EXPOSE 8501

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=10s \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8501/_stcore/health')" || exit 1

# Run the Streamlit dashboard
CMD ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]
