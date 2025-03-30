# c:\Users\CodeX\Meta trade\trading_system\data\__init__.py
import MetaTrader5 as mt5
import pandas as pd
import logging

class DataProcessor:
    def __init__(self, config):
        self.config = config
        self.symbol = config.get("symbol", "XAUUSD")
        self.timeframe_map = {
            "1H": mt5.TIMEFRAME_H1,
            "4H": mt5.TIMEFRAME_H4,
            "D1": mt5.TIMEFRAME_D1
        }

    def fetch_data(self, symbol, timeframe, start, end):
        """Fetch market data from MT5."""
        mt5_timeframe = self.timeframe_map.get(timeframe, mt5.TIMEFRAME_H1)
        rates = mt5.copy_rates_range(symbol, mt5_timeframe, start, end)
        if rates is None:
            logging.error(f"Failed to fetch data for {symbol}")
            return None
        df = pd.DataFrame(rates)
        df["time"] = pd.to_datetime(df["time"], unit="s")
        return df

    def calculate_indicators(self, data):
        """Calculate technical indicators (placeholder)."""
        # Add real indicator logic here (e.g., RSI, MA) as needed
        # For now, return raw data
        return data

    def normalize_data(self, data):
        """Normalize data for model input (placeholder)."""
        # Add normalization logic (e.g., Min-Max scaling) as needed
        return data