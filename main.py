from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, PlainTextResponse
from fastapi.templating import Jinja2Templates
from client import MCPClient  # Import your MCPClient class
import asyncio

app = FastAPI()

# Initialize Jinja2 templates
templates = Jinja2Templates(directory="templates")

# Initialize the MCP client
client = MCPClient()
server_connected = False

@app.on_event("startup")
async def startup_event():
    global server_connected
    try:
        print("Attempting to connect to server...")
        await client.connect_to_server("yahoo_finance.py")
        print("Successfully connected to server.")
        server_connected = True
    except Exception as e:
        print(f"Failed to connect to server: {str(e)}")

@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    """
    Serve the main dashboard UI.
    """
    return templates.TemplateResponse("index.html", {"request": request})

@app.post("/api/query")
async def process_query(query: dict):
    if not server_connected:
        raise HTTPException(status_code=500, detail="Not connected to MCP server")
    
    user_query = query.get("query")
    if not user_query:
        raise HTTPException(status_code=400, detail="Query is required")
    
    try:
        response = await client.process_query(user_query)
        return {"response": response}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/favicon.ico")
async def favicon():
    """
    Suppress favicon requests to avoid 404 errors.
    """
    return PlainTextResponse(content="", status_code=204)

@app.on_event("shutdown")
async def shutdown_event():
    await client.cleanup()