#!/bin/bash

# Start the Yahoo Finance MCP server in the background
uv run /app/mcp-client/yahoo_finance.py &

# Wait for the server to initialize (optional, adjust sleep time if needed)
sleep 5

# Start the FastAPI app (UI) using Uvicorn
uvicorn main:app --host 0.0.0.0 --port 8000 --reload

