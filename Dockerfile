# Multi-stage build for Flask CRM application

# Stage 1: Node.js for Tailwind CSS build
FROM node:18-alpine AS tailwind-builder

WORKDIR /app

# Copy package files
COPY package*.json ./
COPY tailwind.config.js ./
COPY postcss.config.js ./

# Install Node dependencies (including dev dependencies for build tools)
RUN npm ci

# Copy static source files
COPY app/static/src ./app/static/src
COPY app/templates ./app/templates

# Build Tailwind CSS
RUN npm run build:css

# Stage 2: Python application
FROM python:3.11-slim

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Create non-root user
RUN useradd -m -u 1000 appuser && \
    mkdir -p /app && \
    chown -R appuser:appuser /app

WORKDIR /app

# Install system dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    gcc \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt && \
    pip install --no-cache-dir gunicorn

# Copy application code
COPY . .

# Copy built Tailwind CSS from previous stage
COPY --from=tailwind-builder /app/app/static/css/output.css ./app/static/css/output.css

# Create necessary directories and fix ownership
RUN mkdir -p /app/instance && \
    chown -R appuser:appuser /app

# Switch to non-root user
USER appuser

# Expose port
EXPOSE 8080

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=40s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8080/', timeout=2)" || exit 1

# Run with gunicorn
# Using fewer workers and threads to reduce memory usage
# Worker timeout increased to handle slow database connections
CMD ["gunicorn", "--bind", "0.0.0.0:8080", "--workers", "1", "--threads", "8", "--timeout", "120", "--worker-class", "gthread", "--worker-tmp-dir", "/dev/shm", "--graceful-timeout", "30", "--keep-alive", "5", "--access-logfile", "-", "--error-logfile", "-", "--log-level", "info", "run:app"]
