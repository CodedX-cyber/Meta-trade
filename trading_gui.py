import json
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                           QHBoxLayout, QLabel, QTreeWidget, QTreeWidgetItem, 
                           QTextEdit, QFrame, QSplitter, QPushButton, QStatusBar,
                           QLineEdit, QComboBox, QMessageBox, QFileDialog, QCheckBox)
from PyQt5.QtCore import Qt, QTimer, pyqtSignal
from PyQt5.QtGui import QPalette, QColor, QFont, QIcon
import MetaTrader5 as mt5
import pandas as pd
from datetime import datetime
import sys
import pyqtgraph as pg
import numpy as np
from ta import add_all_ta_features
from trading_bot import get_market_data, calculate_indicators
from trading_monitor import TradingMonitor

class TradingBotGUI(QMainWindow):
    refresh_signal = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.symbol = "XAUUSD"
        self.command_file = "trading_command.txt"
        self.monitor = TradingMonitor()
        if not self.monitor.initialize():
            QMessageBox.critical(self, "Error", "Failed to initialize MetaTrader5")
            sys.exit(1)
        self.initUI()
        
        # Setup update timer
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_all)
        self.timer.start(5000)  # Update every 5 seconds
        self.refresh_signal.connect(self.update_all)
        self.trading_active = False

    def initUI(self):
        self.setWindowTitle('Trading Bot Dashboard')
        self.setGeometry(100, 100, 1000, 600)  # Reduced from 1200x800 to 1000x600
        self.setWindowIcon(QIcon('icon.png'))  # Optional: Add an icon file

        # Create main widget and layout
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        layout = QVBoxLayout(main_widget)

        # Create control panel
        self.create_control_panel(layout)
        
        # Create header with refresh button
        self.create_header(layout)
        
        # Create main content area with splitter
        self.create_main_content(layout)
        
        # Create bottom panel
        self.create_bottom_panel(layout)

        # Add status bar
        self.statusBar = QStatusBar()
        self.setStatusBar(self.statusBar)
        self.statusBar.showMessage("Ready", 5000)

    def create_control_panel(self, parent_layout):
        control_widget = QWidget()
        control_layout = QHBoxLayout(control_widget)

        # Set Trade Button and Inputs
        self.order_type = QComboBox()
        self.order_type.addItems(["Buy", "Sell"])
        control_layout.addWidget(QLabel("Order Type:"))
        control_layout.addWidget(self.order_type)

        self.lot_size = QLineEdit("0.1")
        control_layout.addWidget(QLabel("Lot Size:"))
        control_layout.addWidget(self.lot_size)

        self.auto_sl_tp = QCheckBox("Auto SL/TP")
        self.auto_sl_tp.setChecked(True)
        control_layout.addWidget(self.auto_sl_tp)

        self.sl_input = QLineEdit()
        control_layout.addWidget(QLabel("Stop Loss (optional):"))
        control_layout.addWidget(self.sl_input)

        self.tp_input = QLineEdit()
        control_layout.addWidget(QLabel("Take Profit (optional):"))
        control_layout.addWidget(self.tp_input)

        set_trade_button = QPushButton("Set Trade")
        set_trade_button.clicked.connect(self.set_trade)
        control_layout.addWidget(set_trade_button)

        # Start/Stop Trading Button
        self.toggle_trading_button = QPushButton("Start Trading")
        self.toggle_trading_button.clicked.connect(self.toggle_trading)
        control_layout.addWidget(self.toggle_trading_button)

        # Stop Trade Button
        stop_trade_button = QPushButton("Stop Trade")
        stop_trade_button.clicked.connect(self.stop_trade)
        control_layout.addWidget(stop_trade_button)

        # Generate and Export Report Buttons
        report_button = QPushButton("Generate Report")
        report_button.clicked.connect(self.generate_report)
        control_layout.addWidget(report_button)

        export_button = QPushButton("Export Report")
        export_button.clicked.connect(self.export_report)
        control_layout.addWidget(export_button)

        parent_layout.addWidget(control_widget)

    def create_header(self, parent_layout):
        header_widget = QWidget()
        header_layout = QHBoxLayout(header_widget)

        # Account info label
        self.account_label = QLabel("Account Info: Loading...")
        self.account_label.setFont(QFont("Arial", 12, QFont.Bold))
        header_layout.addWidget(self.account_label)

        # Refresh button
        refresh_button = QPushButton("Refresh")
        refresh_button.clicked.connect(self.refresh_signal.emit)
        header_layout.addWidget(refresh_button)

        # Status label
        self.status_label = QLabel("Status: Connecting...")
        self.status_label.setFont(QFont("Arial", 10))
        header_layout.addWidget(self.status_label, alignment=Qt.AlignRight)

        parent_layout.addWidget(header_widget)

    def create_main_content(self, parent_layout):
        splitter = QSplitter(Qt.Horizontal)

        # Left panel - Chart
        chart_widget = QWidget()
        chart_layout = QVBoxLayout(chart_widget)
        
        # Setup pyqtgraph GraphicsLayoutWidget for multiple plots
        self.plot_layout = pg.GraphicsLayoutWidget()
        self.plot_layout.setBackground('w')  # Set background on GraphicsLayoutWidget
        self.price_plot = self.plot_layout.addPlot(title="Price Chart", row=0, col=0)
        self.price_plot.showGrid(x=True, y=True)
        self.price_plot.setLabel('left', 'Price')
        self.price_plot.setLabel('bottom', 'Time')
        self.rsi_plot = self.plot_layout.addPlot(title="RSI", row=1, col=0)
        self.rsi_plot.setYRange(0, 100)
        chart_layout.addWidget(self.plot_layout)
        
        splitter.addWidget(chart_widget)

        # Right panel
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)

        # Positions widget (collapsible)
        positions_frame = QFrame()
        positions_frame.setFrameStyle(QFrame.StyledPanel)
        positions_layout = QVBoxLayout(positions_frame)
        
        positions_label = QLabel("Active Positions")
        positions_label.setFont(QFont("Arial", 12, QFont.Bold))
        positions_layout.addWidget(positions_label)
        
        self.positions_tree = QTreeWidget()
        self.positions_tree.setHeaderLabels(["Type", "Volume", "Price", "Profit"])
        self.positions_tree.setFont(QFont("Arial", 10))
        self.positions_tree.setColumnWidth(0, 80)
        self.positions_tree.setColumnWidth(1, 80)
        self.positions_tree.setColumnWidth(2, 100)
        self.positions_tree.setColumnWidth(3, 100)
        positions_layout.addWidget(self.positions_tree)
        
        right_layout.addWidget(positions_frame)

        # Indicators widget (collapsible)
        indicators_frame = QFrame()
        indicators_frame.setFrameStyle(QFrame.StyledPanel)
        indicators_layout = QVBoxLayout(indicators_frame)
        
        indicators_label = QLabel("Technical Indicators")
        indicators_label.setFont(QFont("Arial", 12, QFont.Bold))
        indicators_layout.addWidget(indicators_label)
        
        self.indicators_text = QTextEdit()
        self.indicators_text.setReadOnly(True)
        self.indicators_text.setFont(QFont("Arial", 10))
        indicators_layout.addWidget(self.indicators_text)
        
        right_layout.addWidget(indicators_frame)
        
        splitter.addWidget(right_panel)
        splitter.setStretchFactor(0, 2)  # Chart takes more space
        splitter.setStretchFactor(1, 1)  # Right panel takes less
        parent_layout.addWidget(splitter)

    def create_bottom_panel(self, parent_layout):
        bottom_frame = QFrame()
        bottom_frame.setFrameStyle(QFrame.StyledPanel)
        bottom_layout = QVBoxLayout(bottom_frame)
        
        log_label = QLabel("Trading Log")
        log_label.setFont(QFont("Arial", 12, QFont.Bold))
        bottom_layout.addWidget(log_label)
        
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setFont(QFont("Arial", 10))
        bottom_layout.addWidget(self.log_text)
        
        parent_layout.addWidget(bottom_frame)

    def update_account_info(self):
        if mt5.initialize():
            account_info = mt5.account_info()
            if account_info:
                info_text = f"Balance: ${account_info.balance:.2f} | Equity: ${account_info.equity:.2f} | Profit: ${account_info.profit:.2f}"
                self.account_label.setText(info_text)
                self.status_label.setText("Status: Connected")
                self.statusBar.showMessage("Connected to MetaTrader5", 3000)
            else:
                self.status_label.setText("Status: Error getting account info")
                self.statusBar.showMessage("Error fetching account info", 3000)
        else:
            self.status_label.setText("Status: Disconnected")
            self.statusBar.showMessage("Disconnected from MetaTrader5", 3000)

    def update_positions(self):
        self.positions_tree.clear()
        positions = mt5.positions_get(symbol=self.symbol)
        
        if positions:
            for position in positions:
                item = QTreeWidgetItem([
                    "Buy" if position.type == 0 else "Sell",
                    str(position.volume),
                    str(position.price_open),
                    f"${position.profit:.2f}"
                ])
                # Color coding for profit/loss
                profit = float(position.profit)
                item.setForeground(3, QColor('green' if profit >= 0 else 'red'))
                self.positions_tree.addTopLevelItem(item)
                # Add tooltip
                item.setToolTip(3, f"Profit/Loss: ${position.profit:.2f} as of {datetime.now().strftime('%H:%M:%S')}")

    def update_indicators(self):
        rates = mt5.copy_rates_from_pos(self.symbol, mt5.TIMEFRAME_H1, 0, 100)
        if rates is not None:
            df = pd.DataFrame(rates)
            # Add all technical indicators using ta library
            df = add_all_ta_features(df, open="open", high="high", low="low", close="close", volume="tick_volume")
            indicators_text = (
                f"Current Price: ${df['close'].iloc[-1]:.2f}\n"
                f"RSI: {df['momentum_rsi'].iloc[-1]:.2f}\n"
                f"MACD: {df['trend_macd'].iloc[-1]:.2f}\n"
                f"EMA50: {df['trend_ema_fast'].iloc[-1]:.2f}\n"  # Note: Adjust if needed for specific 50-period EMA
                f"EMA200: {df['trend_ema_slow'].iloc[-1]:.2f}\n"  # Note: Adjust if needed for specific 200-period EMA
            )
            self.indicators_text.setText(indicators_text)
            self.current_data = df  # Store for chart

    def update_chart(self):
        try:
            if hasattr(self, 'current_data') and self.current_data is not None:
                df = self.current_data
                # Limit to last 50 points to reduce rendering load
                max_points = min(50, len(df))
                df = df.iloc[-max_points:]
                time_index = range(max_points)
                
                # Clear previous plots
                self.price_plot.clear()
                self.rsi_plot.clear()
                
                # Plot close prices with tooltip
                price_curve = self.price_plot.plot(time_index, df['close'].values, pen='b', name='Price')
                price_curve.curve.setClickable(True)
                price_curve.sigClicked.connect(lambda x, y: self.statusBar.showMessage(f"Price clicked at: ${df['close'].iloc[int(x[-1]) % max_points]:.2f}", 2000))
                
                # Plot technical indicators (EMA50 and EMA200)
                self.price_plot.plot(time_index, df['trend_ema_fast'].values, pen='r', name='EMA50')
                self.price_plot.plot(time_index, df['trend_ema_slow'].values, pen='g', name='EMA200')
                
                # Plot RSI
                self.rsi_plot.plot(time_index, df['momentum_rsi'].values, pen='y', name='RSI')
                
        except Exception as e:
            self.add_log_message(f"Error updating chart: {str(e)}")

    def add_log_message(self, message):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.log_text.append(f"{timestamp}: {message}")

    def update_all(self):
        try:
            self.statusBar.showMessage("Updating data...", 2000)
            self.update_account_info()
            self.update_positions()
            self.update_indicators()
            self.update_chart()
            self.add_log_message("Data updated successfully")
            self.statusBar.showMessage("Data updated successfully", 2000)
            if self.trading_active:
                self.monitor_active_trades()
        except Exception as e:
            self.add_log_message(f"Error updating data: {str(e)}")
            self.statusBar.showMessage(f"Error: {str(e)}", 2000)

    def set_trade(self):
        try:
            order_type = mt5.ORDER_TYPE_BUY if self.order_type.currentText() == "Buy" else mt5.ORDER_TYPE_SELL
            lot = float(self.lot_size.text())
            if not self.lot_size.text() or lot <= 0:
                raise ValueError("Lot size must be a positive number")

            rates = get_market_data(self.symbol, mt5.TIMEFRAME_H1)
            if rates is None:
                raise ValueError("Failed to fetch market data")
            df = calculate_indicators(rates)
            atr = df['ATR'].iloc[-1] if 'ATR' in df.columns and not pd.isna(df['ATR'].iloc[-1]) else 10.0

            price = mt5.symbol_info_tick(self.symbol).ask if order_type == mt5.ORDER_TYPE_BUY else mt5.symbol_info_tick(self.symbol).bid
            if self.auto_sl_tp.isChecked():
                sl = price - (atr * 1.5) if order_type == mt5.ORDER_TYPE_BUY else price + (atr * 1.5)
                tp = price + (atr * 2.5) if order_type == mt5.ORDER_TYPE_BUY else price - (atr * 2.5)
            else:
                sl = float(self.sl_input.text()) if self.sl_input.text() and float(self.sl_input.text()) else None
                tp = float(self.tp_input.text()) if self.tp_input.text() and float(self.tp_input.text()) else None
                if sl and (sl >= price if order_type == mt5.ORDER_TYPE_BUY else sl <= price):
                    raise ValueError("Stop Loss must be below current price for Buy or above for Sell")
                if tp and (tp <= price if order_type == mt5.ORDER_TYPE_BUY else tp >= price):
                    raise ValueError("Take Profit must be above current price for Buy or below for Sell")

            with open(self.command_file, 'w') as f:
                f.write(json.dumps({
                    "command": "place_order",
                    "params": {
                        "symbol": self.symbol,
                        "order_type": "buy" if order_type == mt5.ORDER_TYPE_BUY else "sell",
                        "lot": lot,
                        "sl": sl,
                        "tp": tp
                    }
                }))
            self.add_log_message(f"Trade command sent: {self.order_type.currentText()} {lot} lots, SL: {sl:.2f}, TP: {tp:.2f}")
        except ValueError as e:
            self.add_log_message(f"Invalid input: {str(e)}")
        except Exception as e:
            self.add_log_message(f"Error setting trade: {str(e)}")

    def toggle_trading(self):
        self.trading_active = not self.trading_active
        self.toggle_trading_button.setText("Stop Trading" if self.trading_active else "Start Trading")
        with open(self.command_file, 'w') as f:
            f.write(json.dumps({"command": "toggle_trading", "params": {"active": self.trading_active}}))
        self.add_log_message(f"Trading {'started' if self.trading_active else 'stopped'}")

    def stop_trade(self):
        positions = mt5.positions_get(symbol=self.symbol)
        if positions:
            for position in positions:
                request = {
                    "action": mt5.TRADE_ACTION_DEAL,
                    "position": position.ticket,
                    "symbol": self.symbol,
                    "volume": position.volume,
                    "type": mt5.ORDER_TYPE_CLOSE_BY if position.type == 0 else mt5.ORDER_TYPE_SELL,
                    "price": mt5.symbol_info_tick(self.symbol).bid if position.type == 0 else mt5.symbol_info_tick(self.symbol).ask,
                    "deviation": 5,
                    "magic": 123456,
                    "comment": "Manual Close",
                    "type_time": mt5.ORDER_TIME_GTC,
                    "type_filling": mt5.ORDER_FILLING_FOK,
                }
                result = mt5.order_send(request)
                if result and result.retcode == mt5.TRADE_RETCODE_DONE:
                    self.add_log_message(f"Trade closed successfully: Ticket {position.ticket}")
                else:
                    self.add_log_message(f"Failed to close trade {position.ticket}: {result.retcode if result else 'No result'}")
        else:
            self.add_log_message("No active positions to close")

    def generate_report(self):
        performance = self.monitor.analyze_completed_trades(days_back=30)
        if performance:
            report = (
                f"Total Trades: {performance['total_trades']}\n"
                f"Win Rate: {performance['win_rate']:.2f}%\n"
                f"Total Profit: ${performance['total_profit']:.2f}\n"
                f"Average Win: ${performance['average_win']:.2f}\n"
                f"Average Loss: ${performance['average_loss']:.2f}\n"
                f"Profit Factor: {performance['profit_factor']:.2f}"
            )
            self.log_text.append("\n--- Trade Performance Report ---\n" + report)
        else:
            self.add_log_message("Failed to generate report")

    def export_report(self):
        performance = self.monitor.analyze_completed_trades(days_back=30)
        if performance:
            report = (
                f"Total Trades: {performance['total_trades']}\n"
                f"Win Rate: {performance['win_rate']:.2f}%\n"
                f"Total Profit: ${performance['total_profit']:.2f}\n"
                f"Average Win: ${performance['average_win']:.2f}\n"
                f"Average Loss: ${performance['average_loss']:.2f}\n"
                f"Profit Factor: {performance['profit_factor']:.2f}"
            )
            file_name, _ = QFileDialog.getSaveFileName(self, "Save Report", "", "Text Files (*.txt)")
            if file_name:
                with open(file_name, 'w') as f:
                    f.write("--- Trade Performance Report ---\n" + report)
                self.add_log_message(f"Report exported to {file_name}")
        else:
            self.add_log_message("Failed to export report: No data available")

    def monitor_active_trades(self):
        positions = mt5.positions_get(symbol=self.symbol)
        if positions:
            for position in positions:
                current_price = mt5.symbol_info_tick(self.symbol).bid if position.type == 0 else mt5.symbol_info_tick(self.symbol).ask
                unrealized_pnl = position.volume * (current_price - position.price_open)
                account_info = mt5.account_info()
                if account_info:
                    loss_limit = -account_info.balance * 0.02  # 2% loss limit
                    if unrealized_pnl < loss_limit:
                        self.stop_trade_for_position(position.ticket)
                        self.add_log_message(f"Trade closed due to loss limit: Ticket {position.ticket}, PnL: ${unrealized_pnl:.2f}")

    def stop_trade_for_position(self, ticket):
        position = next((p for p in mt5.positions_get() if p.ticket == ticket), None)
        if position:
            request = {
                "action": mt5.TRADE_ACTION_DEAL,
                "position": position.ticket,
                "symbol": self.symbol,
                "volume": position.volume,
                "type": mt5.ORDER_TYPE_CLOSE_BY if position.type == 0 else mt5.ORDER_TYPE_SELL,
                "price": mt5.symbol_info_tick(self.symbol).bid if position.type == 0 else mt5.symbol_info_tick(self.symbol).ask,
                "deviation": 5,
                "magic": 123456,
                "comment": "Loss Limit Close",
                "type_time": mt5.ORDER_TIME_GTC,
                "type_filling": mt5.ORDER_FILLING_FOK,
            }
            result = mt5.order_send(request)
            if result and result.retcode == mt5.TRADE_RETCODE_DONE:
                self.add_log_message(f"Trade closed due to loss limit: Ticket {ticket}")
            else:
                self.add_log_message(f"Failed to close trade {ticket}: {result.retcode if result else 'No result'}")

def main():
    app = QApplication(sys.argv)
    
    # Set the style to fusion for a modern look
    app.setStyle('Fusion')
    
    # Create dark palette
    palette = QPalette()
    palette.setColor(QPalette.Window, QColor(53, 53, 53))
    palette.setColor(QPalette.WindowText, Qt.white)
    palette.setColor(QPalette.Base, QColor(35, 35, 35))
    palette.setColor(QPalette.AlternateBase, QColor(53, 53, 53))
    palette.setColor(QPalette.ToolTipBase, Qt.white)
    palette.setColor(QPalette.ToolTipText, Qt.white)
    palette.setColor(QPalette.Text, Qt.white)
    palette.setColor(QPalette.Button, QColor(53, 53, 53))
    palette.setColor(QPalette.ButtonText, Qt.white)
    palette.setColor(QPalette.BrightText, Qt.red)
    palette.setColor(QPalette.Link, QColor(42, 130, 218))
    palette.setColor(QPalette.Highlight, QColor(42, 130, 218))
    palette.setColor(QPalette.HighlightedText, Qt.black)
    
    app.setPalette(palette)
    
    ex = TradingBotGUI()
    ex.show()
    sys.exit(app.exec_())

if __name__ == '__main__':
    main()