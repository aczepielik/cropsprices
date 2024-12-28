# Use Python 3.9+ slim image
FROM python:3.12-slim

# Add build arguments
ARG APP_ENV=staging
ARG PROJECT_ID

# Set environment variables
ENV APP_ENV=$APP_ENV
ENV PROJECT_ID=$PROJECT_ID

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

# Copy requirements first to leverage Docker cache
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Expose port 8080 (Cloud Run will override this with PORT environment variable) 
EXPOSE 8080

# Run the application
CMD exec python -m main