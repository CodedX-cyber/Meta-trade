import asyncio
import logging
from mcp import ClientSession, CallToolRequest
from mcp.client.stdio import stdio_client
import pandas as pd
import sys
import os

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.FileHandler("trading_bot.log"), logging.StreamHandler()],
)

# Global client session to be set in main()
client_session = None

async def get_market_data(symbol, timeframe):
    """Fetch market data from the MCP server."""
    try:
        request = CallToolRequest(
            method="tools/call",
            params={"name": "get_market_data", "symbol": symbol, "timeframe": timeframe},
        )
        response = await client_session.send_request(request, result_type=dict)
        if response.get("success", False):
            data = response.get("data", [])
            df = pd.DataFrame(data)
            logging.info(f"Retrieved {len(df)} rows of market data for {symbol} on {timeframe}")
            return df
        else:
            raise RuntimeError(response.get("error", "Unknown error"))
    except Exception as e:
        logging.error(f"Error in get_market_data: {str(e)}")
        return None

async def place_order(symbol, order_type, lot, sl, tp):
    """Place an order using the MCP server."""
    try:
        request = CallToolRequest(
            method="tools/call",
            params={
                "name": "place_order",
                "symbol": symbol,
                "order_type": order_type,
                "lot": lot,
                "sl": sl,
                "tp": tp,
            },
        )
        response = await client_session.send_request(request, result_type=dict)
        if response.get("success", False):
            logging.info(f"Order placed successfully: {response.get('result')}")
            return response.get("result")
        else:
            raise RuntimeError(response.get("error", "Unknown error"))
    except Exception as e:
        logging.error(f"Error in place_order: {str(e)}")
        return None

class ServerProcess:
    """A class that mimics the expected interface for stdio_client."""
    def __init__(self, command, args):
        self.command = command
        self.args = args
        self.env = os.environ  # Set the environment variables
        self.encoding = 'utf-8'  # Set the encoding attribute
        self.encoding_error_handler = 'replace'  # Set the encoding error handler

async def main():
    """Main function to start the trading bot."""
    global client_session
    
    # Create a server object with command and args attributes
    server = ServerProcess(sys.executable, ["mcp_server.py"])
    
    # This should match the expected interface for stdio_client
    async with stdio_client(server=server) as (read_stream, write_stream):
        client_session = ClientSession(read_stream, write_stream)
        
        # Example usage
        df = await get_market_data("XAUUSD", "1H")
        if df is not None:
            logging.info(f"Market data: {df.tail()}")
        
        order_result = await place_order("XAUUSD", "buy", 0.1, 1800, 1850)
        if order_result is not None:
            logging.info(f"Order result: {order_result}")

if __name__ == "__main__":
    asyncio.run(main())