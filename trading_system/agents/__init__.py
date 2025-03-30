# c:\Users\CodeX\Meta trade\trading_system\agents\__init__.py
import MetaTrader5 as mt5
import logging

from trading_system.models import TradingTransformer

class TradingAgent:
    def __init__(self, config):
        self.config = config
        self.model = TradingTransformer()  # Initialize the model

    def execute_trade(self, symbol, prediction, current_price):
        """Execute a trade based on prediction."""
        order_type = mt5.ORDER_TYPE_BUY if prediction > 0 else mt5.ORDER_TYPE_SELL
        lot = float(self.config.get("lot", 0.1))
        sl = current_price - 10 if order_type == mt5.ORDER_TYPE_BUY else current_price + 10
        tp = current_price + 20 if order_type == mt5.ORDER_TYPE_BUY else current_price - 20

        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": symbol,
            "volume": lot,
            "type": order_type,
            "price": current_price,
            "sl": sl,
            "tp": tp,
            "deviation": 10,
            "magic": 123456,
            "comment": "TradingAgent Trade",
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_FOK,
        }
        result = mt5.order_send(request)
        if result.retcode == mt5.TRADE_RETCODE_DONE:
            logging.info(f"Trade executed: {result}")
        else:
            logging.error(f"Trade failed: {result.retcode}")