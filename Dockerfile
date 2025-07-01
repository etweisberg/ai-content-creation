FROM python:3.13-slim

WORKDIR /app

# Copy dependency files
COPY pyproject.toml uv.lock README.md ./

# Create minimal package structure for hatchling
RUN mkdir -p sloppy && touch sloppy/__init__.py

# Install dependencies (this layer will be cached)
RUN pip install uv && uv sync

# Copy actual source code (this layer changes frequently)
COPY sloppy/ ./sloppy/

CMD ["uv", "run", "celery", "-A", "sloppy.celery_app", "worker", "--loglevel=info"]