import MetaTrader5 as mt5
import pandas as pd
from datetime import datetime, timedelta
import logging
import time

# Setup logging
logging.basicConfig(
    filename='trading_monitor.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

class TradingMonitor:
    def __init__(self):
        self.symbol = "XAUUSD"
        self.initial_balance = None
        self.trade_history = []
        
    def initialize(self):
        if not mt5.initialize():
            logging.error("Failed to initialize MT5")
            return False
        self.initial_balance = mt5.account_info().balance
        return True

    def monitor_active_positions(self):
        """Monitor currently open positions"""
        positions = mt5.positions_get(symbol=self.symbol)
        
        if positions is None:
            logging.info("No open positions")
            return []
        
        position_data = []
        for position in positions:
            current_price = mt5.symbol_info_tick(self.symbol).bid if position.type == 0 else mt5.symbol_info_tick(self.symbol).ask
            unrealized_pnl = position.volume * (current_price - position.price_open)
            risk_percent = abs(position.price_open - position.sl) / position.price_open * 100
            
            position_info = {
                'ticket': position.ticket,
                'type': 'BUY' if position.type == 0 else 'SELL',
                'volume': position.volume,
                'open_price': position.price_open,
                'current_price': current_price,
                'sl': position.sl,
                'tp': position.tp,
                'unrealized_pnl': unrealized_pnl,
                'risk_percent': risk_percent
            }
            position_data.append(position_info)
            
            # Log warnings for risk management
            if risk_percent > 2:  # Warning if risk is more than 2% per trade
                logging.warning(f"High risk position detected: {risk_percent:.2f}% on ticket {position.ticket}")
                
        return position_data

    def analyze_completed_trades(self, days_back=30):
        """Analyze completed trades from the past X days"""
        from_date = datetime.now() - timedelta(days=days_back)
        
        # Get historical trades
        trades = mt5.history_deals_get(from_date, datetime.now())
        if trades is None:
            logging.error("Failed to get trade history")
            return None
            
        trades_df = pd.DataFrame(list(trades), columns=trades[0]._asdict().keys())
        
        # Calculate key metrics
        total_trades = len(trades_df)
        winning_trades = len(trades_df[trades_df['profit'] > 0])
        losing_trades = len(trades_df[trades_df['profit'] <= 0])
        win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0
        
        total_profit = trades_df['profit'].sum()
        average_win = trades_df[trades_df['profit'] > 0]['profit'].mean() if winning_trades > 0 else 0
        average_loss = trades_df[trades_df['profit'] <= 0]['profit'].mean() if losing_trades > 0 else 0
        
        return {
            'total_trades': total_trades,
            'win_rate': win_rate,
            'total_profit': total_profit,
            'average_win': average_win,
            'average_loss': average_loss,
            'profit_factor': abs(average_win / average_loss) if average_loss != 0 else 0
        }

    def check_position_sizing(self):
        """Verify position sizing is within acceptable limits"""
        account_info = mt5.account_info()
        if account_info is None:
            logging.error("Failed to get account info")
            return False
            
        balance = account_info.balance
        positions = mt5.positions_get(symbol=self.symbol)
        
        if positions is None:
            return True
            
        total_exposure = sum(pos.volume for pos in positions)
        exposure_percent = (total_exposure * 100000) / balance  # Assuming standard lot size
        
        if exposure_percent > 20:  # Warning if total exposure is more than 20% of account
            logging.warning(f"High total exposure: {exposure_percent:.2f}% of account balance")
            return False
            
        return True

    def run_monitoring(self):
        """Main monitoring loop"""
        while True:
            try:
                # Monitor active positions
                active_positions = self.monitor_active_positions()
                for position in active_positions:
                    logging.info(f"Active Position: {position}")

                # Analyze recent trading performance
                performance = self.analyze_completed_trades()
                if performance:
                    logging.info(f"Trading Performance: {performance}")

                # Check position sizing
                position_sizing_ok = self.check_position_sizing()
                if not position_sizing_ok:
                    logging.warning("Position sizing check failed")

                # Calculate drawdown
                current_balance = mt5.account_info().balance
                drawdown = ((self.initial_balance - current_balance) / self.initial_balance) * 100
                if drawdown > 10:  # Warning if drawdown exceeds 10%
                    logging.warning(f"High drawdown alert: {drawdown:.2f}%")

            except Exception as e:
                logging.error(f"Monitoring error: {str(e)}")
            
            time.sleep(300)  # Check every 5 minutes

if __name__ == "__main__":
    monitor = TradingMonitor()
    if monitor.initialize():
        monitor.run_monitoring() 