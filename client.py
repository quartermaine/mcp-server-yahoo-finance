import asyncio
from typing import Optional
from contextlib import AsyncExitStack

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from openai import AzureOpenAI
from dotenv import load_dotenv
import os
import json
import sys

# Load environment variables from .env file
load_dotenv()

class MCPClient:
    def __init__(self):
        # Initialize session and client objects
        self.session = None  # Session object
        self.exit_stack = AsyncExitStack()  # Exit stack for async resources
        self.client = AzureOpenAI(
            api_version=os.environ.get("AZURE_OPEN_AI_API_VERSION"),
            azure_endpoint=os.environ.get("AZURE_OPEN_AI_ENDPOINT"),
            api_key=os.environ.get("AZURE_OPEN_AI_API_KEY")
        )

    async def connect_to_server(self, server_script_path):
        """Connect to an MCP server."""
        if not server_script_path.endswith(".py") and not server_script_path.endswith(".js"):
            print("Error: Server script must be .py or .js")
            return
        
        command = "python" if server_script_path.endswith(".py") else "node"
        params = StdioServerParameters(command=command, args=[server_script_path], env=None)
        
        transport = await self.exit_stack.enter_async_context(stdio_client(params))
        self.stdio, self.write = transport
        self.session = await self.exit_stack.enter_async_context(ClientSession(self.stdio, self.write))
        
        await self.session.initialize()
        
        # List available tools
        response = await self.session.list_tools()
        tools = getattr(response, "tools", [])
        if len(tools) == 0:
            print("\nNo tools found on the server.")
        else:
            tool_names = []
            for tool in tools:
                tool_names.append(tool.name)
            print("\nConnected to server with tools:", tool_names)

    async def process_query(self, query: str) -> str:
        """Process a query using Azure OpenAI and available tools."""
        messages = [
            {
                "role": "user",
                "content": query
            }
        ]

        # List available tools from the server
        response = await self.session.list_tools()
        available_tools = [
            {
                "type": "function",
                "function": {
                    "name": tool.name,
                    "description": tool.description,
                    "parameters": tool.inputSchema
                }
            }
            for tool in getattr(response, "tools", [])
        ]

        # Initial Azure OpenAI API call
        try:
            response = self.client.chat.completions.create(
                model=os.environ.get("AZURE_OPEN_AI_DEPLOYMENT_MODEL"),
                messages=messages,
                tools=available_tools,
                temperature=0.5,
                max_tokens=1000
            )
        except Exception as e:
            return f"Error calling Azure OpenAI API: {str(e)}"

        final_text = []
        tool_results = []

        # Process the response and handle tool calls
        for choice in response.choices:
            message = choice.message

            # Handle text responses
            if message.content:
                final_text.append(message.content)

            # Handle tool calls
            if hasattr(message, "tool_calls") and message.tool_calls:
                for tool_call in message.tool_calls:
                    tool_name = tool_call.function.name
                    tool_args = tool_call.function.arguments
                    tool_call_id = tool_call.id

                    # Deserialize arguments
                    try:
                        tool_args = json.loads(tool_args)
                    except json.JSONDecodeError as e:
                        return f"Error parsing JSON: {str(e)}"

                    # Execute the tool call
                    try:
                        if tool_name == "get_stock_price":
                            symbol = tool_args.get("symbol")
                            result = await self.session.call_tool(tool_name, {"symbol": symbol})
                        elif tool_name == "get_company_info":
                            symbol = tool_args.get("symbol")
                            result = await self.session.call_tool(tool_name, {"symbol": symbol})
                        elif tool_name == "get_historical_data":
                            symbol = tool_args.get("symbol")
                            start_date = tool_args.get("start_date")
                            end_date = tool_args.get("end_date")
                            result = await self.session.call_tool(
                                tool_name, {"symbol": symbol, "start_date": start_date, "end_date": end_date}
                            )
                        else:
                            return f"Error: Unknown tool name: {tool_name}"

                        # Extract plain text from the result
                        try:
                            content = result.content
                            if isinstance(content, list) and len(content) > 0 and hasattr(content[0], "text"):
                                result_text = content[0].text
                            else:
                                result_text = str(result)
                        except Exception as e:
                            result_text = f"[Error extracting result text: {str(e)}]"

                        final_text.append(f"[Calling tool {tool_name} with args {tool_args}]")
                        final_text.append(result_text)
                        tool_results.append({"call": tool_name, "result": result_text})

                    except Exception as e:
                        return f"Error executing tool {tool_name}: {str(e)}"

                    # Append the tool response message
                    messages.append({"role": "assistant", "tool_calls": [tool_call]})
                    messages.append({"role": "tool", "tool_call_id": tool_call_id, "content": str(result.content)})

        return "\n".join(final_text)

    async def chat_loop(self):
        """Run an interactive chat loop."""
        print("\nMCP Client Started!")
        print("Type your queries or 'quit' to exit.")
        
        while True:
            try:
                query = input("\nQuery: ").strip()
                
                if query.lower() == "quit":
                    break
                
                response = await self.process_query(query)
                print("\n" + response)
                    
            except Exception as e:
                print(f"\nError: {str(e)}")
    
    async def cleanup(self):
        """Clean up resources."""
        await self.exit_stack.aclose()


async def main():
    if len(sys.argv) < 2:
        print("Usage: python client.py C:\\path\\to\\server_script.py")
        sys.exit(1)
        
    client = MCPClient()
    try:
        await client.connect_to_server(sys.argv[1])
        await client.chat_loop()
    finally:
        await client.cleanup()

if __name__ == "__main__":
    asyncio.run(main())
    
# Query: Get current price of AAPL

# Query: Get historical data for AAPL from 2023-01-01 to 2023-01-31

# Query: Give me informantion about AAPL

