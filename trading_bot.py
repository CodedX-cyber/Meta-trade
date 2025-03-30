# trading_bot.py (MCP version, modified)
import asyncio
import logging
from mcp import ClientSession, CallToolRequest
from mcp.client.stdio import stdio_client
import sys
import os
import json

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.FileHandler("trading_bot.log"), logging.StreamHandler()],
)

client_session = None

async def start_trading_algorithm(config):
    """Start the trading algorithm on the server."""
    try:
        request = CallToolRequest(
            method="tools/call",
            params={"name": "run_trading_algorithm", "config": config},
        )
        response = await client_session.send_request(request, result_type=dict)
        if response.get("success", False):
            logging.info(f"Trading algorithm started: {response.get('message')}")
            return True
        else:
            raise RuntimeError(response.get("error", "Unknown error"))
    except Exception as e:
        logging.error(f"Error starting trading algorithm: {str(e)}")
        return False

class ServerProcess:
    def __init__(self, command, args):
        self.command = command
        self.args = args
        self.env = os.environ
        self.encoding = 'utf-8'
        self.encoding_error_handler = 'replace'

async def main():
    global client_session
    server = ServerProcess(sys.executable, ["mcp_server_fixed.py"])
    
    async with stdio_client(server=server) as (read_stream, write_stream):
        client_session = ClientSession(read_stream, write_stream)
        
        # Load configuration
        with open('mcp.config.json', 'r') as f:
            config = json.load(f)
        
        await start_trading_algorithm(config)

if __name__ == "__main__":
    asyncio.run(main())