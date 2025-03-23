# test_bot.py

import MetaTrader5 as mt5
import pandas as pd
import numpy as np
from datetime import datetime

def test_mt5_connection():
    """Test MT5 connection"""
    if not mt5.initialize():
        print("MT5 initialization failed")
        return False
    print("\nMT5 Connection Test:")
    print("--------------------")
    print(f"MT5 Terminal Info: {mt5.terminal_info()}")
    print(f"MT5 Version: {mt5.version()}")
    return True

def test_symbol_data():
    """Test symbol data availability"""
    symbol = "XAUUSD"
    symbol_info = mt5.symbol_info(symbol)
    
    print("\nSymbol Data Test:")
    print("----------------")
    if symbol_info is None:
        print(f"Symbol {symbol} not found")
        return False
    
    print(f"Symbol: {symbol_info.name}")
    print(f"Point value: {symbol_info.point}")
    print(f"Trade modes: {symbol_info.trade_mode}")
    print(f"Current Bid: {symbol_info.bid}")
    print(f"Current Ask: {symbol_info.ask}")
    return True

def test_market_data():
    """Test market data retrieval"""
    symbol = "XAUUSD"
    timeframe = mt5.TIMEFRAME_H1
    
    rates = mt5.copy_rates_from_pos(symbol, timeframe, 0, 10)
    
    print("\nMarket Data Test:")
    print("----------------")
    if rates is None:
        print("Failed to retrieve market data")
        return False
    
    df = pd.DataFrame(rates)
    df["time"] = pd.to_datetime(df["time"], unit="s")
    print("\nLast 5 candles:")
    print(df.tail())
    return True

def run_tests():
    """Run all tests"""
    print("Starting Trading Bot Tests")
    print("=========================")
    
    tests = [
        test_mt5_connection,
        test_symbol_data,
        test_market_data
    ]
    
    all_passed = True
    for test in tests:
        try:
            if not test():
                all_passed = False
                print(f"\nTest {test.__name__} failed!")
        except Exception as e:
            all_passed = False
            print(f"\nError in {test.__name__}: {str(e)}")
    
    return all_passed

if __name__ == "__main__":
    try:
        success = run_tests()
        if success:
            print("\nAll tests passed! You can now run the trading bot.")
        else:
            print("\nSome tests failed. Please fix the issues before running the trading bot.")
    finally:
        mt5.shutdown()