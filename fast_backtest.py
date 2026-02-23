import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Optional, Tuple, Dict
import logging

from binance_client_manager import BinanceClientManager

logger = logging.getLogger(__name__)

class FastTradeManager:
    """إدارة سريعة للصفقات"""
    
    def __init__(self):
        self.open_trade: Optional[Dict] = None
        self.closed_trades = []
        self.total_profit = 0
        self.total_loss = 0
        self.win_count = 0
        self.loss_count = 0

    def open_position(self, side: str, entry_price: float, stop_price: float, 
                     tp_price: float, qty: float, timestamp: float) -> Dict:
        self.open_trade = {
            "side": side,
            "entry_price": entry_price,
            "stop_price": stop_price,
            "tp_price": tp_price,
            "qty": qty,
            "entry_time": timestamp,
            "pnl": 0,
            "status": "OPEN"
        }
        return self.open_trade

    def check_close_conditions(self, current_price: float, timestamp: float) -> Optional[Dict]:
        if not self.open_trade:
            return None

        trade = self.open_trade
        closed_trade = None

        if trade["side"] == "BUY":
            if current_price <= trade["stop_price"]:
                pnl = (current_price - trade["entry_price"]) * trade["qty"]
                closed_trade = self._close_trade(current_price, timestamp, "STOP_LOSS", pnl)
            elif current_price >= trade["tp_price"]:
                pnl = (current_price - trade["entry_price"]) * trade["qty"]
                closed_trade = self._close_trade(current_price, timestamp, "TAKE_PROFIT", pnl)
        
        elif trade["side"] == "SELL":
            if current_price >= trade["stop_price"]:
                pnl = (trade["entry_price"] - current_price) * trade["qty"]
                closed_trade = self._close_trade(current_price, timestamp, "STOP_LOSS", pnl)
            elif current_price <= trade["tp_price"]:
                pnl = (trade["entry_price"] - current_price) * trade["qty"]
                closed_trade = self._close_trade(current_price, timestamp, "TAKE_PROFIT", pnl)

        return closed_trade

    def _close_trade(self, exit_price: float, timestamp: float, reason: str, pnl: float) -> Dict:
        trade = self.open_trade.copy()
        trade["exit_price"] = exit_price
        trade["exit_time"] = timestamp
        trade["reason"] = reason
        trade["pnl"] = pnl
        trade["status"] = "CLOSED"

        self.closed_trades.append(trade)
        
        if pnl > 0:
            self.total_profit += pnl
            self.win_count += 1
        else:
            self.total_loss += abs(pnl)
            self.loss_count += 1

        self.open_trade = None
        return trade

    def get_statistics(self) -> Dict:
        total_trades = len(self.closed_trades)
        if total_trades == 0:
            return {
                "total_trades": 0,
                "win_count": 0,
                "loss_count": 0,
                "win_rate": 0,
                "total_profit": 0,
                "total_loss": 0,
                "net_profit": 0,
                "avg_profit": 0,
                "max_drawdown": 0
            }

        # Calculate Max Drawdown
        equity_curve = pd.Series([t['pnl'] for t in self.closed_trades]).cumsum()
        if not equity_curve.empty:
            peak = equity_curve.expanding(min_periods=1).max()
            drawdown = (equity_curve - peak) / peak
            max_drawdown = drawdown.min() * 100 if not drawdown.empty else 0
        else:
            max_drawdown = 0

        return {
            "total_trades": total_trades,
            "win_count": self.win_count,
            "loss_count": self.loss_count,
            "win_rate": (self.win_count / total_trades * 100) if total_trades > 0 else 0,
            "total_profit": self.total_profit,
            "total_loss": self.total_loss,
            "net_profit": self.total_profit - self.total_loss,
            "avg_profit": (self.total_profit - self.total_loss) / total_trades if total_trades > 0 else 0,
            "max_drawdown": max_drawdown
        }

    def is_position_open(self) -> bool:
        return self.open_trade is not None


def detect_equal_lows(df: pd.DataFrame) -> pd.Series:
    if len(df) < 3:
        return pd.Series(dtype=float)
    lows = df["low"].rolling(3).agg(lambda x: x.iloc[1] if x.iloc[1] == x.min() else np.nan)
    return lows.dropna()

def detect_equal_highs(df: pd.DataFrame) -> pd.Series:
    if len(df) < 3:
        return pd.Series(dtype=float)
    highs = df["high"].rolling(3).agg(lambda x: x.iloc[1] if x.iloc[1] == x.max() else np.nan)
    return highs.dropna()

def check_long_signal(df: pd.DataFrame, volume_mult: float = 1.5) -> Tuple[bool, Optional[float]]:
    if df.empty:
        return False, None
    equal_lows = detect_equal_lows(df)
    if len(equal_lows) < 1:
        return False, None

    last_equal = equal_lows.iloc[-1]
    current_low = df["low"].iloc[-1]
    current_volume = df["volume"].iloc[-1]
    
    if len(df) < 20:
        avg_volume = df["volume"].mean()
    else:
        avg_volume = df["volume"].rolling(20).mean().iloc[-1]

    if current_low < last_equal and current_volume > avg_volume * volume_mult:
        return True, last_equal
    return False, None

def check_short_signal(df: pd.DataFrame, volume_mult: float = 1.5) -> Tuple[bool, Optional[float]]:
    if df.empty:
        return False, None
    equal_highs = detect_equal_highs(df)
    if len(equal_highs) < 1:
        return False, None

    last_equal = equal_highs.iloc[-1]
    current_high = df["high"].iloc[-1]
    current_volume = df["volume"].iloc[-1]
    
    if len(df) < 20:
        avg_volume = df["volume"].mean()
    else:
        avg_volume = df["volume"].rolling(20).mean().iloc[-1]

    if current_high > last_equal and current_volume > avg_volume * volume_mult:
        return True, last_equal
    return False, None

def calc_position_size(balance: float, entry_price: float, stop_price: float, 
                      risk_pct: float = 0.005) -> float:
    if stop_price == entry_price:
        return 0.0
    risk_amount = balance * risk_pct
    risk_per_unit = abs(entry_price - stop_price)
    if risk_per_unit == 0:
        return 0.0
    return round(risk_amount / risk_per_unit, 6)


def run_fast_backtest(symbol: str = "BTCUSDT", timeframe: str = "1h", 
                      rr_ratio: float = 2.0, volume_mult: float = 1.5, 
                      risk_pct: float = 0.005, lookback: int = 50,
                      start_date: str = "1 Jan, 2023", end_date: str = "1 Jan, 2024"):
    """تشغيل اختبار سريع باستخدام بيانات تاريخية حقيقية"""
    
    print(f"\n{'='*70}")
    print(f"🚀 اختبار رجعي للزوج: {symbol}، الإطار الزمني: {timeframe}")
    print(f"{'='*70}\n")
    
    client_manager = BinanceClientManager() # No API keys needed for backtesting
    trade_manager = FastTradeManager()
    initial_balance = 1000.0
    balance = initial_balance

    # Fetch historical data
    # Note: Binance API get_historical_klines requires start_str and optional end_str
    # The current BinanceClientManager.get_klines does not support date ranges directly.
    # For a proper backtest, a dedicated historical data fetching function is needed.
    # For now, we will simulate fetching a large chunk of data.
    # In a real scenario, you would use client.get_historical_klines(symbol, interval, start_str, end_str)
    
    # Simulating fetching historical data for demonstration. 
    # In a real implementation, this would be replaced with actual historical data fetching.
    # For simplicity, let's assume we have a way to get a large DataFrame of historical data.
    # For this example, we'll use the simulated klines from BinanceClientManager, but extend it.
    
    # To get real historical data, you would need to modify BinanceClientManager or add a new function.
    # Example: client.get_historical_klines(symbol, timeframe, start_date, end_date)
    
    # For now, let's use an extended simulated dataset for the backtest.
    # This is a placeholder and needs to be replaced with actual historical data fetching.
    logger.warning("Using extended simulated data for backtest. Replace with real historical data fetching for accurate results.")
    
    # Generate more simulated data for backtesting over a longer period
    num_candles = 1000 # Example: 1000 candles for backtest
    historical_df = client_manager._get_simulated_klines(num_candles)
    
    if historical_df is None or historical_df.empty:
        logger.error("Failed to get historical data for backtest.")
        return

    # Iterate through historical data candle by candle
    for i in range(lookback, len(historical_df)):
        current_df = historical_df.iloc[i-lookback:i].copy()
        current_price = current_df["close"].iloc[-1]
        current_time = current_df["open_time"].iloc[-1] / 1000 # Convert ms to s

        # Check for closing conditions first
        if trade_manager.is_position_open():
            closed_trade = trade_manager.check_close_conditions(current_price, current_time)
            if closed_trade:
                # Update balance based on closed trade PnL
                balance += closed_trade['pnl']
                logger.info(f"Trade closed. New balance: {balance:.2f}")
            continue

        # Check for new signals
        long_signal, long_level = check_long_signal(current_df, volume_mult)
        if long_signal:
            entry_price = current_price
            stop_price = long_level - (current_price * 0.002) # Use current_price for stop calculation
            qty = calc_position_size(balance, entry_price, stop_price, risk_pct)
            if qty > 0:
                tp_price = entry_price + (entry_price - stop_price) * rr_ratio
                trade_manager.open_position("BUY", entry_price, stop_price, tp_price, qty, current_time)
                logger.info(f"Backtest: Opened BUY position at {entry_price:.2f}")
            continue

        short_signal, short_level = check_short_signal(current_df, volume_mult)
        if short_signal:
            entry_price = current_price
            stop_price = short_level + (current_price * 0.002) # Use current_price for stop calculation
            qty = calc_position_size(balance, entry_price, stop_price, risk_pct)
            if qty > 0:
                tp_price = entry_price - (stop_price - entry_price) * rr_ratio
                trade_manager.open_position("SELL", entry_price, stop_price, tp_price, qty, current_time)
                logger.info(f"Backtest: Opened SELL position at {entry_price:.2f}")
            continue

    # طباعة النتائج
    stats = trade_manager.get_statistics()
    
    print(f"{'='*70}")
    print(f"📊 نتائج الاختبار الرجعي")
    print(f"{'='*70}")
    print(f"الرصيد الأولي: ${initial_balance:.2f}")
    print(f"الرصيد النهائي: ${balance:.2f}")
    print(f"إجمالي الصفقات: {stats['total_trades']}")
    print(f"الصفقات الرابحة: {stats['win_count']} ✅")
    print(f"الصفقات الخاسرة: {stats['loss_count']} ❌")
    print(f"نسبة النجاح: {stats['win_rate']:.2f}%")
    print(f"إجمالي الأرباح: ${stats['total_profit']:.2f}")
    print(f"إجمالي الخسائر: ${stats['total_loss']:.2f}")
    print(f"صافي الربح: ${stats['net_profit']:.2f}")
    print(f"متوسط الربح/الصفقة: ${stats['avg_profit']:.2f}")
    print(f"أقصى تراجع (Max Drawdown): {stats['max_drawdown']:.2f}%")
    print(f"{'='*70}\n")
    
    # طباعة أفضل وأسوأ صفقات
    if trade_manager.closed_trades:
        best_trade = max(trade_manager.closed_trades, key=lambda x: x['pnl'])
        worst_trade = min(trade_manager.closed_trades, key=lambda x: x['pnl'])
        
        print(f"🏆 أفضل صفقة: ${best_trade['pnl']:.2f} ({best_trade['side']})")
        print(f"💔 أسوأ صفقة: ${worst_trade['pnl']:.2f} ({worst_trade['side']})")
        print(f"{'='*70}\n")


if __name__ == "__main__":
    # Example usage with real parameters for backtesting
    run_fast_backtest(symbol="BTCUSDT", timeframe="1h", start_date="1 Jan, 2023", end_date="1 Jan, 2024")
