# Use a base image with a shell
FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim

# Set working directory
WORKDIR /app/mcp-client

# Copy all Python files and the templates directory
COPY *.py /app/mcp-client/
COPY templates /app/mcp-client/templates
COPY .env /app/mcp-client/.env
COPY start.sh /app/mcp-client/start.sh

# Install dependencies into the system environment
RUN uv pip install --system fastapi jinja2 uvicorn mcp anthropic python-dotenv openai yfinance

# Ensure yahoo_finance.py is executable
RUN chmod +x yahoo_finance.py

# Expose port
EXPOSE 8000

# Copy and set permissions for the startup script
COPY start.sh /app/start.sh
RUN chmod +x /app/start.sh

# Set the entrypoint
CMD ["/app/start.sh"]


