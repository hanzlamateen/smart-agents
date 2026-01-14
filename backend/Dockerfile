FROM python:3.11-slim

# Prevent Python from writing .pyc files (bytecode cache) to disk, keeping the container filesystem clean and avoiding stale cache issues.
ENV PYTHONDONTWRITEBYTECODE=1

# Force Python's stdout/stderr to be unbuffered. This is crucial for Docker because it ensures logs appear immediately in docker logs without being held in a buffer.
ENV PYTHONUNBUFFERED=1

# Required for ComputerTool
ARG DISPLAY_NUM=1
ARG HEIGHT=768
ARG WIDTH=1024
ENV DISPLAY_NUM=$DISPLAY_NUM
ENV HEIGHT=$HEIGHT
ENV WIDTH=$WIDTH

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    git \
    openssh-client \
    && rm -rf /var/lib/apt/lists/*

# Install poetry
RUN curl -sSL https://install.python-poetry.org | python3 -
ENV PATH="/root/.local/bin:$PATH"

# Configure poetry
RUN poetry config virtualenvs.create false

# Copy dependency files
COPY pyproject.toml poetry.lock* ./

# Install dependencies
RUN poetry install --no-interaction --no-ansi

# Copy app code
COPY app/ ./app/

# Start Orchestrator
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]
