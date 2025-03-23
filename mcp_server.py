# Metadata
# Path: mcp_server_fixed.py
# Repo: Meta trade
# Owner: CodeX
# Branch: main

import asyncio
import logging
import MetaTrader5 as mt5
from mcp.server import Server  # Ensure this is the correct import
from mcp.server.stdio import stdio_server
import pandas as pd
import sys
import json
import csv
import os

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
        
        # Map timeframe to MT5 constants
        timeframe_map = {
            "1H": mt5.TIMEFRAME_H1,
            "4H": mt5.TIMEFRAME_H4,
            "D1": mt5.TIMEFRAME_D1,
        }
        mt5_timeframe = timeframe_map.get(timeframe, mt5.TIMEFRAME_H1)
        
        # Fetch rates
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
        
        # Map order type to MT5 constants
        mt5_order_type = mt5.ORDER_TYPE_BUY if order_type == "buy" else mt5.ORDER_TYPE_SELL
        
        # Get current price
        price = mt5.symbol_info_tick(symbol).ask if order_type == "buy" else mt5.symbol_info_tick(symbol).bid
        
        # Create order request
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
        
        # Send order
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
        # Assuming request_data is a JSONRPCMessage, extract the 'params' or 'method' as needed
        if hasattr(request_data, 'json'):
            return request_data.json  # Adjust based on the actual structure of JSONRPCMessage
        else:
            raise TypeError("Invalid request data format")
    except Exception as e:
        logging.error(f"Failed to parse request: {str(e)}")
        return {"success": False, "error": "Invalid request format"}

def analyze_csv_file(file_path):
    """Analyze a CSV file to detect its format and potential issues."""
    if not os.path.exists(file_path):
        logging.error(f"File not found: {file_path}")
        return {"error": "File not found"}
    
    # Try to detect encoding and delimiters
    encodings = ['cp1252', 'utf-8', 'latin1']
    delimiters = [',', ';', '\t', '|']
    result = {}
    
    # Try to read the first few lines with different encodings
    for encoding in encodings:
        try:
            with open(file_path, 'r', encoding=encoding) as f:
                # Read up to 10 lines for analysis
                lines = []
                for _ in range(10):
                    line = f.readline()
                    if not line:
                        break
                    lines.append(line)
                
                if lines:
                    # We found a working encoding
                    result["detected_encoding"] = encoding
                    
                    # Count delimiters in each line to detect the most likely delimiter
                    delimiter_counts = {}
                    for delimiter in delimiters:
                        delimiter_counts[delimiter] = [line.count(delimiter) for line in lines]
                    
                    result["delimiter_analysis"] = delimiter_counts
                    
                    # Check for inconsistent field counts
                    field_counts = {}
                    for delimiter in delimiters:
                        fields_per_line = [len(line.split(delimiter)) for line in lines]
                        if len(set(fields_per_line)) > 1:
                            # Inconsistent field counts with this delimiter
                            field_counts[delimiter] = fields_per_line
                        else:
                            field_counts[delimiter] = fields_per_line[0] if fields_per_line else 0
                    
                    result["field_counts"] = field_counts
                    
                    # Find the most likely delimiter (one with consistent, non-zero field counts)
                    for delimiter in delimiters:
                        counts = delimiter_counts.get(delimiter, [])
                        if counts and all(count > 1 for count in counts) and len(set(counts)) <= 1:
                            result["likely_delimiter"] = delimiter
                            break
                    
                    # Sample the first few lines for display
                    result["sample_lines"] = lines[:5]
                    break
            
        except Exception as e:
            logging.debug(f"Error analyzing with encoding {encoding}: {str(e)}")
            continue
    
    if "detected_encoding" not in result:
        result["error"] = "Could not determine file encoding"
    
    return result

def load_data_from_csv(file_path):
    """Load data from a CSV file with robust error handling and format detection."""
    # First analyze the CSV to determine its structure
    analysis = analyze_csv_file(file_path)
    logging.info(f"CSV Analysis: {analysis}")
    
    # List of encoding types to try
    encodings = [analysis.get("detected_encoding", "cp1252"), 'utf-8', 'latin1']
    
    # List of delimiter characters to try
    delimiters = [analysis.get("likely_delimiter", ","), ',', ';', '\t', '|']
    
    for encoding in encodings:
        for delimiter in delimiters:
            try:
                # Use pandas with the detected parameters and error handling
                df = pd.read_csv(
                    file_path,
                    encoding=encoding,
                    sep=delimiter,
                    quoting=csv.QUOTE_MINIMAL,      # Handle quoted fields
                    on_bad_lines='warn',            # Warn about bad lines
                    low_memory=False,                # Better handling for mixed data types
                    skipinitialspace=True,          # Skip spaces after delimiter
                    header=0,                       # Treat the first row as the header
                )
                
                # Clean the DataFrame by dropping empty columns and rows
                df.dropna(axis=1, how='all', inplace=True)  # Drop columns that are completely empty
                df.dropna(axis=0, how='all', inplace=True)  # Drop rows that are completely empty
                
                # Drop columns that are unnamed
                df = df.loc[:, ~df.columns.str.contains('^Unnamed')]
                
                # If we got here, the parsing succeeded
                logging.info(f"Successfully loaded CSV with delimiter='{delimiter}', encoding='{encoding}'")
                logging.info(f"Loaded {len(df)} rows with {len(df.columns)} columns from {file_path}")
                
                # Log the column headers for debugging
                logging.info(f"CSV columns: {df.columns.tolist()}")
                
                return df
                
            except Exception as e:
                # If this combination failed, log and try the next one
                logging.debug(f"Attempt with delimiter='{delimiter}', encoding='{encoding}' failed: {str(e)}")
                continue
    
    # If we've tried all combinations and none worked, try one more approach
    try:
        # Try reading with Python's built-in CSV module first to detect format
        with open(file_path, 'r', encoding='cp1252') as csvfile:
            dialect = csv.Sniffer().sniff(csvfile.read(4096))
            csvfile.seek(0)
            
            logging.info(f"CSV Sniffer detected delimiter: '{dialect.delimiter}'")
            
            # Now try pandas with the detected dialect
            df = pd.read_csv(
                file_path,
                encoding='cp1252',
                sep=dialect.delimiter,
                quoting=csv.QUOTE_MINIMAL,
                on_bad_lines='warn',            # Warn about bad lines
                low_memory=False
            )
            
            logging.info(f"Successfully loaded CSV using detected dialect")
            logging.info(f"Loaded {len(df)} rows with {len(df.columns)} columns from {file_path}")
            
            return df
            
    except Exception as e:
        logging.error(f"Final CSV loading attempt failed: {str(e)}")
    
    # If all attempts failed
    logging.error(f"Failed to load CSV file {file_path} after trying multiple formats")
    return None

async def main():
    """Main function to start the MCP server."""
    try:
        if not await initialize_mt5():
            logging.error("Failed to initialize MetaTrader5, exiting...")
            sys.exit(1)

        logging.info("TradingBot MCP server setup starting...")
        
        # First analyze the CSV file
        logging.info("Analyzing CSV file before loading...")
        analysis_result = analyze_csv_file('large_file.csv')
        logging.info(f"CSV Analysis Result: {analysis_result}")
        
        # Then try to load it with our enhanced loader
        df = load_data_from_csv('large_file.csv')
        if df is not None:
            logging.info(f"Data from CSV: {df.head()}")  # Log the first few rows of the DataFrame
        else:
            logging.error("Failed to load the CSV file after multiple attempts")
        
        async with stdio_server() as (read_stream, write_stream):
            server = Server(read_stream, write_stream)  # Ensure this is the correct instantiation
            
            # Handle incoming requests directly
            while True:
                request_data = await read_stream.receive()  # Read the incoming request from the stream
                request = parse_request(request_data)  # Parse the request
                
                if isinstance(request, dict) and request.get("method") == "get_market_data":
                    response = await get_market_data(request.get("params", {}))
                elif isinstance(request, dict) and request.get("method") == "place_order":
                    response = await place_order(request.get("params", {}))
                else:
                    response = {"success": False, "error": "Unknown method"}
                
                # Ensure write_stream has the correct method to send data
                if hasattr(write_stream, 'send'):
                    await write_stream.send(json.dumps(response).encode('utf-8'))  # Send the response
                else:
                    logging.error("write_stream does not have a send method")

    except Exception as e:
        logging.error(f"Unexpected error in main: {str(e)}", exc_info=True)
        raise

if __name__ == "__main__":
    asyncio.run(main())