import asyncio
from typing import Optional
from contextlib import AsyncExitStack

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from openai import AzureOpenAI, OpenAI
from dotenv import load_dotenv
import os
import json 

load_dotenv()  # load environment variables from .env

class MCPClient:
    def __init__(self):
        # Initialize session and client objects
        self.session: Optional[ClientSession] = None
        self.exit_stack = AsyncExitStack()
        # self.anthropic = Anthropic()
        self.client = AzureOpenAI(
            api_version=os.environ.get("AZURE_OPEN_AI_API_VERSION", None),
            azure_endpoint=os.environ.get("AZURE_OPEN_AI_ENDPOINT", None),
            api_key=os.environ.get("AZURE_OPEN_AI_API_KEY", None),
        )

    async def connect_to_server(self, server_script_path: str):
        """Connect to an MCP server
        
        Args:
            server_script_path: Path to the server script (.py or .js)
        """
        is_python = server_script_path.endswith('.py')
        is_js = server_script_path.endswith('.js')
        if not (is_python or is_js):
            raise ValueError("Server script must be a .py or .js file")
            
        command = "python" if is_python else "node"
        server_params = StdioServerParameters(
            command=command,
            args=[server_script_path],
            env=None
        )
        
        stdio_transport = await self.exit_stack.enter_async_context(stdio_client(server_params))
        self.stdio, self.write = stdio_transport
        self.session = await self.exit_stack.enter_async_context(ClientSession(self.stdio, self.write))
        
        await self.session.initialize()
        
        # List available tools
        response = await self.session.list_tools()
        tools = response.tools
        print("\nConnected to server with tools:", [tool.name for tool in tools])

    async def process_query(self, query: str) -> str:
        """Process a query using Azure OpenAI and available tools"""
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
                "type": "function",  # Add the required "type" property
                "function": {
                    "name": tool.name,
                    "description": tool.description,
                    "parameters": tool.inputSchema  # Use the input schema directly
                }
            }
            for tool in response.tools
        ]

        # Initial Azure OpenAI API call
        response = self.client.chat.completions.create(
            model=os.environ.get("AZURE_OPEN_AI_DEPLOYMENT_MODEL", None),
            messages=messages,
            tools=available_tools,  # Pass the correctly formatted tools
            temperature=0.5,
            max_tokens=1000
        )

        final_text = []

        # Handle the initial response
        for choice in response.choices:
            message = choice.message

            # Handle text responses
            if message.content:
                final_text.append(message.content)
                # print(f"final text: {final_text}")

            # Handle tool calls
            if hasattr(message, 'tool_calls') and message.tool_calls:
                for tool_call in message.tool_calls:
                    tool_name = tool_call.function.name
                    tool_args = tool_call.function.arguments
                    tool_call_id = tool_call.id  # Extract the tool_call_id

                    # Deserialize the arguments from JSON string to dictionary
                    try:
                        tool_args = json.loads(tool_args)  # Convert JSON string to dictionary
                    except json.JSONDecodeError:
                        return f"Error: Invalid JSON in tool arguments: {tool_args}"

                    # Execute the tool call based on the tool name
                    try:
                        if tool_name == "get_stock_price":
                            symbol = tool_args.get("symbol")
                            result = await self.session.call_tool(tool_name, {"symbol": symbol})  # Pass as dictionary
                        elif tool_name == "get_company_info":
                            symbol = tool_args.get("symbol")
                            result = await self.session.call_tool(tool_name, {"symbol": symbol})  # Pass as dictionary
                        elif tool_name == "get_historical_data":
                            symbol = tool_args.get("symbol")
                            start_date = tool_args.get("start_date")
                            end_date = tool_args.get("end_date")
                            result = await self.session.call_tool(
                                tool_name, {"symbol": symbol, "start_date": start_date, "end_date": end_date}
                            )  # Pass as dictionary

                        else:
                            return f"Error: Unknown tool name: {tool_name}"
                            
                        # Debug the result object
                        # print("Result Object:", result)

                        # Try to extract text from TextContent inside result["content"]
                        try:
                            text_contents = result.content  # Assuming `result` is an object, not a dict
                            if isinstance(text_contents, list) and hasattr(text_contents[0], "text"):
                                result_text = text_contents[0].text
                            else:
                                result_text = str(result)
                        except Exception as e:
                            result_text = f"[Error extracting result text: {str(e)}]"

                        final_text.append(f"[Calling tool {tool_name} with args {tool_args}]")
                        final_text.append(result_text)  # Append only the plain text

                    except Exception as e:
                        return f"Error executing tool {tool_name}: {str(e)}"

                    # Append the tool response message to the conversation
                    messages.append({
                        "role": "assistant",
                        "tool_calls": [tool_call]  # Include the tool call in the assistant message
                    })
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call_id,  # Match the tool_call_id
                        "content": str(result.content)  # Convert result.content to string
                    })

        return "\n".join(final_text)

    async def chat_loop(self):
        """Run an interactive chat loop"""
        print("\nMCP Client Started!")
        print("Type your queries or 'quit' to exit.")
        
        while True:
            try:
                query = input("\nQuery: ").strip()
                
                if query.lower() == 'quit':
                    break
                    
                response = await self.process_query(query)
                print("\n" + response)
                    
            except Exception as e:
                print(f"\nError: {str(e)}")
    
    async def cleanup(self):
        """Clean up resources"""
        await self.exit_stack.aclose()

async def main():
    if len(sys.argv) < 2:
        print("Usage: python client.py C:\\Users\\andreas.christopoulo\\Desktop\\mcp-server\\weather.py")
        sys.exit(1)
        
    client = MCPClient()
    try:
        await client.connect_to_server(sys.argv[1])
        await client.chat_loop()
    finally:
        await client.cleanup()

if __name__ == "__main__":
    import sys
    asyncio.run(main())




# Query: Get current price of AAPL

# Query: Get historical data for AAPL from 2023-01-01 to 2023-01-31

# Query: Give me informantion about AAPL

