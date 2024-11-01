FROM node:20.9.0-alpine3.18 as builder

WORKDIR /app

# Copy package files
COPY package*.json ./

# Install dependencies
RUN npm ci

# Copy source code
COPY . .

# Build frontend
RUN npm run build

FROM python:3.11.6-slim-bullseye

WORKDIR /app

# Install system dependencies and certificates
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    curl \
    ca-certificates \
    dnsutils \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Create certificates directory
RUN mkdir -p /app/backend/certs

# Copy Python requirements and install dependencies
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN pip install open-interpreter==0.3.14


# Copy certificate file
COPY backend/services/cert.crt /app/backend/certs/

# Copy built frontend and backend code
COPY --from=builder /app/backend ./backend
COPY --from=builder /app/dist ./backend/static

# Create config directory for custom DNS resolution
RUN mkdir -p /etc/docker && \
    echo '{"dns": ["8.8.8.8", "8.8.4.4"]}' > /etc/docker/daemon.json

# Set environment variables
ENV NODE_ENV=production \
    PYTHONUNBUFFERED=1 \
    PORT=8000 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/app \
    REQUESTS_CA_BUNDLE=/app/backend/certs/cert.crt \
    CURL_CA_BUNDLE=/app/backend/certs/cert.crt \
    SSL_CERT_FILE=/app/backend/certs/cert.crt

# Create a non-root user
RUN groupadd -r appuser && useradd -r -g appuser -d /app appuser \
    && chown -R appuser:appuser /app

# Switch to non-root user
USER appuser

# Expose port
EXPOSE 8000

# Healthcheck
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/api/health || exit 1

# Start the application
CMD ["python", "-m", "uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4", "--proxy-headers", "--forwarded-allow-ips", "*"]







