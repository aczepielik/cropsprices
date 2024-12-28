# Use Python 3.12 slim image to match pyproject.toml python version
FROM python:3.12-slim as base

# Set Python environment variables
ENV PYTHONFAULTHANDLER=1 \
    PYTHONHASHSEED=random \
    PYTHONUNBUFFERED=1

# Add build arguments
ARG APP_ENV=staging
ARG PROJECT_ID

# Set environment variables
ENV APP_ENV=$APP_ENV \
    PROJECT_ID=$PROJECT_ID

# Install system dependencies for DuckDB and fonts
RUN apt-get update && apt-get install -y \
    build-essential \
    wget \
    unzip \
    fontconfig \
    fonts-roboto \
    fonts-dejavu \
    fonts-liberation \
    && wget https://github.com/duckdb/duckdb/releases/download/v1.1.3/duckdb_cli-linux-amd64.zip \
    && unzip duckdb_cli-linux-amd64.zip -d /usr/local/bin \
    && chmod +x /usr/local/bin/duckdb \
    && rm duckdb_cli-linux-amd64.zip \
    && rm -rf /var/lib/apt/lists/*

# Refresh font cache
RUN fc-cache -f -v

# Set working directory
WORKDIR /app

# Build stage
FROM base as builder

ENV PIP_DEFAULT_TIMEOUT=100 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1 \
    POETRY_VERSION=1.7.1

RUN pip install "poetry==${POETRY_VERSION}"

# Copy poetry files
COPY pyproject.toml poetry.lock ./
COPY app/ ./app/

# Install dependencies
RUN poetry config virtualenvs.in-project true && \
    poetry install

# Final stage
FROM base as final

# Copy virtual environment and built package
COPY --from=builder /app/.venv /app/.venv
COPY --from=builder /app/app /app/app

# Set working directory
WORKDIR /app

# Set PYTHONPATH to include the current directory
ENV PYTHONPATH=/app

# Expose port 8080 (Cloud Run will override this with PORT environment variable) 
EXPOSE 8080

# Run the application with correct path
CMD ["./.venv/bin/python", "-m", "app.main"]
