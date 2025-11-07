# EmailPilot Simple - Production Dockerfile for Google Cloud Run
# Python 3.11 slim base image for smaller size
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies including Node.js for MCP servers
RUN apt-get update && apt-get install -y \
    gcc \
    curl \
    ca-certificates \
    gnupg \
    && mkdir -p /etc/apt/keyrings \
    && curl -fsSL https://deb.nodesource.com/gpgkey/nodesource-repo.gpg.key | gpg --dearmor -o /etc/apt/keyrings/nodesource.gpg \
    && echo "deb [signed-by=/etc/apt/keyrings/nodesource.gpg] https://deb.nodesource.com/node_20.x nodistro main" | tee /etc/apt/sources.list.d/nodesource.list \
    && apt-get update \
    && apt-get install -y nodejs \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create outputs directory
RUN mkdir -p outputs

# Create non-root user for security
RUN useradd -m -u 1000 emailpilot && \
    chown -R emailpilot:emailpilot /app

# Copy MCP configuration to correct location for emailpilot user
# and update paths from macOS (/opt/anaconda3/bin) to container paths (/usr/local/bin)
COPY .mcp.json /home/emailpilot/.mcp.json.tmp
RUN sed 's|/opt/anaconda3/bin/uvx|/usr/local/bin/uvx|g; s|/opt/anaconda3/bin/python3|/usr/local/bin/python3|g' \
    /home/emailpilot/.mcp.json.tmp > /home/emailpilot/.mcp.json && \
    rm /home/emailpilot/.mcp.json.tmp && \
    chown emailpilot:emailpilot /home/emailpilot/.mcp.json

# Switch to non-root user
USER emailpilot

# Expose port (Cloud Run will set PORT env var)
EXPOSE 8000

# Set environment variable for production
ENV PYTHONUNBUFFERED=1

# Health check - test root endpoint
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/', timeout=5)"

# Run the application
CMD ["python", "api.py"]
