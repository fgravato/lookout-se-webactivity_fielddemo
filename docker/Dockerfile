FROM python:3.11-slim

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Create app user
RUN groupadd -r lookout && useradd -r -g lookout lookout

# Set work directory
WORKDIR /app

# Install system dependencies
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        curl \
        ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements_s3.txt .
RUN pip install --no-cache-dir -r requirements_s3.txt

# Copy application code
COPY lookout_s3_logger.py .
COPY .env* ./

# Create logs directory
RUN mkdir -p /var/log && chown lookout:lookout /var/log

# Switch to non-root user
USER lookout

# Health check
HEALTHCHECK --interval=60s --timeout=10s --start-period=30s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8080/health', timeout=5)" || exit 1

# Expose metrics port (optional)
EXPOSE 8080

# Run the application
CMD ["python", "lookout_s3_logger.py"]
