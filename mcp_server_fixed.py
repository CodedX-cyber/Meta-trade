# Metadata
# Path: mcp_server_fixed.py
# Repo: Meta trade
# Owner: CodeX
# Branch: main

import asyncio
import logging
import MetaTrader5 as mt5
from mcp.server import Server
from mcp.server.stdio import stdio_server
import pandas as pd
import sys
import json
import csv
import os
from trading_system import TradingAgent
from trading_system.data.data_processor import DataProcessor
# Configure logging             
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.FileHandler("mcp_server.log"), logging.StreamHandler()],
)

async def initialize_mt5(max_attempts=5, initial_delay=1):
    """Initialize MetaTrader5 with retries."""
    attempt = 0
    while attempt < max_attempts:
        if mt5.initialize():
            logging.info("MetaTrader5 initialized successfully")
            return True
        delay = initial_delay * (2 ** attempt)
        logging.warning(f"MT5 initialization failed, retrying in {delay} seconds...")
        await asyncio.sleep(delay)
        attempt += 1
    logging.error("MT5 Initialization failed after maximum attempts")
    return False

async def get_market_data(params):
    """Fetch market data for a given symbol and timeframe."""
    try:
        symbol = params.get("symbol", "XAUUSD")
        timeframe = params.get("timeframe", "1H")
        timeframe_map = {"1H": mt5.TIMEFRAME_H1, "4H": mt5.TIMEFRAME_H4, "D1": mt5.TIMEFRAME_D1}
        mt5_timeframe = timeframe_map.get(timeframe, mt5.TIMEFRAME_H1)
        rates = mt5.copy_rates_from_pos(symbol, mt5_timeframe, 0, 1000)
        if rates is not None:
            df = pd.DataFrame(rates)
            df["time"] = pd.to_datetime(df["time"], unit="s")
            logging.info(f"Retrieved {len(df)} rows of market data for {symbol} on {timeframe}")
            return {"success": True, "data": df.to_dict(orient="records")}
        else:
            raise RuntimeError("Failed to retrieve market data")
    except Exception as e:
        logging.error(f"Error in get_market_data: {str(e)}")
        return {"success": False, "error": str(e)}

async def place_order(params):
    """Place an order using MT5."""
    try:
        symbol = params.get("symbol", "XAUUSD")
        order_type = params.get("order_type", "buy")
        lot = float(params.get("lot", 0.1))
        sl = float(params.get("sl", 0))
        tp = float(params.get("tp", 0))
        mt5_order_type = mt5.ORDER_TYPE_BUY if order_type == "buy" else mt5.ORDER_TYPE_SELL
        price = mt5.symbol_info_tick(symbol).ask if order_type == "buy" else mt5.symbol_info_tick(symbol).bid
        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": symbol,
            "volume": lot,
            "type": mt5_order_type,
            "price": price,
            "sl": sl,
            "tp": tp,
            "deviation": 10,
            "magic": 123456,
            "comment": "MCP Order",
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_FOK,
        }
        result = mt5.order_send(request)
        if result.retcode == mt5.TRADE_RETCODE_DONE:
            logging.info(f"Order placed successfully: {result}")
            return {"success": True, "result": result._asdict()}
        else:
            raise RuntimeError(f"Failed to place order: {result.retcode}")
    except Exception as e:
        logging.error(f"Error in place_order: {str(e)}")
        return {"success": False, "error": str(e)}

def parse_request(request_data):
    """Parse the incoming request data."""
    try:
        if hasattr(request_data, 'json'):
            return json.loads(request_data.json)
        else:
            return json.loads(request_data)
    except Exception as e:
        logging.error(f"Failed to parse request: {str(e)}")
        return {"success": False, "error": "Invalid request format"}

async def main():
    """Main function to start the MCP server."""
    try:
        if not await initialize_mt5():
            logging.error("Failed to initialize MetaTrader5, exiting...")
            sys.exit(1)

        logging.info("TradingBot MCP server setup starting...")
        
        # Optional CSV loading
        csv_file = 'large_file.csv'
        df = None
        if os.path.exists(csv_file):
            logging.info("Loading CSV file...")
            try:
                df = pd.read_csv(csv_file)
                logging.info(f"Data from CSV: {df.head()}")
            except Exception as e:
                logging.warning(f"Failed to load CSV: {str(e)}, proceeding without it...")
        else:
            logging.info(f"CSV file {csv_file} not found, skipping...")

        async with stdio_server() as (read_stream, write_stream):
            server = Server(read_stream, write_stream)
            logging.info("Server started and connected successfully")
            
            while True:
                try:
                    request_data = await read_stream.receive()
                    request = parse_request(request_data)
                    
                    if not isinstance(request, dict):
                        response = {"success": False, "error": "Invalid request"}
                    elif request.get("method") == "initialize":
                        response = {"jsonrpc": "2.0", "id": request.get("id"), "result": {"status": "success"}}
                    elif request.get("method") == "get_market_data":
                        response = await get_market_data(request.get("params", {}))
                    elif request.get("method") == "place_order":
                        response = await place_order(request.get("params", {}))
                    else:
                        response = {"success": False, "error": "Unknown method"}
                    
                    await write_stream.send(response)
                except Exception as e:
                    logging.error(f"Error in request handling: {str(e)}", exc_info=True)
                    print(f"Error in request handling: {str(e)}", file=sys.stderr)

    except Exception as e:
        logging.error(f"Unexpected error in main: {str(e)}", exc_info=True)
        print(f"Unexpected error in main: {str(e)}", file=sys.stderr)
        sys.exit(1)

async def run_trading_algorithm(params):
    """Run the trading algorithm server-side."""
    try:
        config = params.get("config", {})
        symbol = config.get("symbol", "XAUUSD")
        timeframe = config.get("timeframe", "1H")
        trading_interval = config.get("trading_interval", 60)
        start = config.get("start")
        end = config.get("end")

        # Initialize components
        data_processor = DataProcessor(config)
        agent = TradingAgent(config)

        while True:
            try:
                # Fetch and process data
                data = data_processor.fetch_data(symbol, timeframe, start, end)
                if data is None:
                    raise RuntimeError("Failed to fetch data")

                # Calculate indicators
                processed_data = data_processor.calculate_indicators(data)

                # Normalize data
                normalized_data = data_processor.normalize_data(processed_data)

                # Make prediction
                prediction = agent.model.predict(normalized_data)

                # Execute trade
                current_price = mt5.symbol_info_tick(symbol).ask
                agent.execute_trade(symbol, prediction, current_price)

                # Sleep for the interval
                await asyncio.sleep(trading_interval)

            except Exception as e:
                logging.error(f"Error in trading loop: {str(e)}")
                await asyncio.sleep(trading_interval)

    except Exception as e:
        logging.error(f"Error starting trading algorithm: {str(e)}")
        return {"success": False, "error": str(e)}

if __name__ == "__main__":
    asyncio.run(main())