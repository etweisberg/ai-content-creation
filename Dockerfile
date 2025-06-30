FROM python:3.13-slim

WORKDIR /app

COPY pyproject.toml uv.lock ./
RUN pip install uv && uv sync

COPY . .

CMD ["uv", "run", "celery", "-A", "sloppy.celery_app", "worker", "--loglevel=info"]