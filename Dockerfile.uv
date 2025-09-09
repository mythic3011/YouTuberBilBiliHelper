# Multi-stage build with uv for ultra-fast builds
FROM python:3.12-slim as base

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy

# Install system dependencies and uv
RUN apt-get update && apt-get install -y \
    ffmpeg \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && pip install --no-cache-dir uv

# Dependencies stage
FROM base as deps

# Copy uv configuration files
COPY pyproject.toml uv.lock* ./

# Install dependencies with uv (much faster than pip)
RUN uv sync --frozen --no-install-project --no-dev

# Final stage
FROM base as final

# Create non-root user
RUN groupadd -r appuser && useradd -r -g appuser appuser

# Copy virtual environment from deps stage
COPY --from=deps --chown=appuser:appuser /.venv /.venv

# Add venv to path
ENV PATH="/.venv/bin:$PATH"

# Set working directory
WORKDIR /app

# Copy application code
COPY --chown=appuser:appuser app/ ./app/
COPY --chown=appuser:appuser pyproject.toml ./

# Create necessary directories
RUN mkdir -p downloads/youtube downloads/bilibili downloads/temp logs config/cookies && \
    chown -R appuser:appuser /app

# Switch to non-root user
USER appuser

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/api/v2/system/health || exit 1

# Expose port
EXPOSE 8000

# Run the application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
