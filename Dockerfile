# Multi-stage build for Flask CRM application

# Stage 1: Node.js for Tailwind CSS build
FROM node:18-alpine AS tailwind-builder

WORKDIR /app

# Copy package files
COPY package*.json ./
COPY tailwind.config.js ./
COPY postcss.config.js ./

# Install Node dependencies
RUN npm ci --only=production

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
COPY --chown=appuser:appuser requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt && \
    pip install --no-cache-dir gunicorn

# Copy application code
COPY --chown=appuser:appuser . .

# Copy built Tailwind CSS from previous stage
COPY --from=tailwind-builder --chown=appuser:appuser /app/app/static/css/output.css ./app/static/css/output.css

# Create necessary directories
RUN mkdir -p /app/instance && \
    chown -R appuser:appuser /app/instance

# Switch to non-root user
USER appuser

# Expose port
EXPOSE 8080

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=40s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8080/', timeout=2)" || exit 1

# Run with gunicorn
CMD ["gunicorn", "--bind", "0.0.0.0:8080", "--workers", "2", "--threads", "4", "--timeout", "60", "--access-logfile", "-", "--error-logfile", "-", "run:app"]
