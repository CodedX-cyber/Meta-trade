import pandas as pd
import json

# Sample log data from your input
logs = [
    {"Timestamp": "2025-03-17T06:35:54.288Z", "Component": "trading_bot", "Level": "info", 
     "Message": "Server transport closed unexpectedly", "Details": "this is likely due to the process exiting early..."},
    {"Timestamp": "2025-03-17T06:42:31.050Z", "Component": "trading_bot", "Level": "info", 
     "Message": "Message from client", "Details": json.dumps({"method": "initialize", "params": {"protocolVersion": "2024-11-05", "capabilities": {}, "clientInfo": {"name": "claude-ai", "version": "0.1.0"}}, "jsonrpc": "2.0", "id": 0})},
    {"Timestamp": "2025-03-17 07:42:58,685", "Component": None, "Level": "ERROR", 
     "Message": "Failed to load CSV file large_file.csv after trying multiple formats", "Details": ""}
]

# Sample market data (mocked, as no real data from logs)
market_data = [
    {"symbol": "XAUUSD", "timeframe": "1H", "time": "2025-03-17 06:00:00", "open": 1800.5, "high": 1805.2, "low": 1798.3, "close": 1802.1},
    {"symbol": "XAUUSD", "timeframe": "1H", "time": "2025-03-17 07:00:00", "open": 1802.1, "high": 1807.0, "low": 1800.0, "close": 1804.5}
]

# Sample order data (mocked, as no real order from logs)
orders = [
    {"symbol": "XAUUSD", "order_type": "buy", "lot": 0.1, "sl": 1800, "tp": 1850, "timestamp": "2025-03-17T06:42:00Z"}
]

# Create DataFrames
df_logs = pd.DataFrame(logs)
df_market = pd.DataFrame(market_data)
df_orders = pd.DataFrame(orders)

# Write to Excel with multiple sheets
with pd.ExcelWriter("trading_bot_summary.xlsx") as writer:
    df_logs.to_excel(writer, sheet_name="Logs", index=False)
    df_market.to_excel(writer, sheet_name="Market Data", index=False)
    df_orders.to_excel(writer, sheet_name="Orders", index=False)

print("Excel file 'trading_bot_summary.xlsx' created successfully.")