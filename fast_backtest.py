"""
اختبار سريع للبوت - بدون تأخيرات زمنية
Fast Backtest - No Sleep Delays
"""

import numpy as np
import pandas as pd
from datetime import datetime
from typing import Optional, Tuple, Dict

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

        if trade["side"] == "BUY" and current_price <= trade["stop_price"]:
            pnl = (current_price - trade["entry_price"]) * trade["qty"]
            closed_trade = self._close_trade(current_price, timestamp, "STOP_LOSS", pnl)
        elif trade["side"] == "SELL" and current_price >= trade["stop_price"]:
            pnl = (trade["entry_price"] - current_price) * trade["qty"]
            closed_trade = self._close_trade(current_price, timestamp, "STOP_LOSS", pnl)
        elif trade["side"] == "BUY" and current_price >= trade["tp_price"]:
            pnl = (current_price - trade["entry_price"]) * trade["qty"]
            closed_trade = self._close_trade(current_price, timestamp, "TAKE_PROFIT", pnl)
        elif trade["side"] == "SELL" and current_price <= trade["tp_price"]:
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
                "avg_profit": 0
            }

        return {
            "total_trades": total_trades,
            "win_count": self.win_count,
            "loss_count": self.loss_count,
            "win_rate": (self.win_count / total_trades * 100) if total_trades > 0 else 0,
            "total_profit": self.total_profit,
            "total_loss": self.total_loss,
            "net_profit": self.total_profit - self.total_loss,
            "avg_profit": (self.total_profit - self.total_loss) / total_trades if total_trades > 0 else 0
        }

    def is_position_open(self) -> bool:
        return self.open_trade is not None


def detect_equal_lows(df: pd.DataFrame) -> pd.Series:
    lows = df["low"].rolling(3).agg(lambda x: x.iloc[1] if x.iloc[1] == x.min() else np.nan)
    return lows.dropna()

def detect_equal_highs(df: pd.DataFrame) -> pd.Series:
    highs = df["high"].rolling(3).agg(lambda x: x.iloc[1] if x.iloc[1] == x.max() else np.nan)
    return highs.dropna()

def check_long_signal(df: pd.DataFrame, volume_mult: float = 1.5) -> Tuple[bool, Optional[float]]:
    equal_lows = detect_equal_lows(df)
    if len(equal_lows) < 1:
        return False, None

    last_equal = equal_lows.iloc[-1]
    current_low = df["low"].iloc[-1]
    current_volume = df["volume"].iloc[-1]
    avg_volume = df["volume"].rolling(20).mean().iloc[-1]

    if current_low < last_equal and current_volume > avg_volume * volume_mult:
        return True, last_equal
    return False, None

def check_short_signal(df: pd.DataFrame, volume_mult: float = 1.5) -> Tuple[bool, Optional[float]]:
    equal_highs = detect_equal_highs(df)
    if len(equal_highs) < 1:
        return False, None

    last_equal = equal_highs.iloc[-1]
    current_high = df["high"].iloc[-1]
    current_volume = df["volume"].iloc[-1]
    avg_volume = df["volume"].rolling(20).mean().iloc[-1]

    if current_high > last_equal and current_volume > avg_volume * volume_mult:
        return True, last_equal
    return False, None

def calc_position_size(balance: float, entry_price: float, stop_price: float, 
                      risk_pct: float = 0.005) -> float:
    risk_amount = balance * risk_pct
    risk_per_unit = abs(entry_price - stop_price)
    if risk_per_unit == 0:
        return 0
    return round(risk_amount / risk_per_unit, 6)


def run_fast_backtest(iterations: int = 500):
    """تشغيل اختبار سريع بدون تأخيرات"""
    
    print(f"\n{'='*70}")
    print(f"🚀 اختبار سريع للبوت - {iterations} تكرار")
    print(f"{'='*70}\n")
    
    trade_manager = FastTradeManager()
    balance = 1000
    
    for iteration in range(iterations):
        # توليد بيانات عشوائية
        data = []
        for i in range(50):
            timestamp = iteration * 60 + i
            open_price = 50000 + np.random.uniform(-200, 200)
            close_price = open_price + np.random.uniform(-100, 100)
            high_price = max(open_price, close_price) + np.random.uniform(0, 100)
            low_price = min(open_price, close_price) - np.random.uniform(0, 100)
            volume = np.random.uniform(100, 1000)
            
            data.append({
                "open": open_price,
                "high": high_price,
                "low": low_price,
                "close": close_price,
                "volume": volume
            })
        
        df = pd.DataFrame(data)
        current_price = df["close"].iloc[-1]
        current_time = iteration

        # التحقق من إغلاق الصفقات
        if trade_manager.is_position_open():
            closed_trade = trade_manager.check_close_conditions(current_price, current_time)
            if closed_trade:
                pass  # لا تطبع
            continue

        # البحث عن إشارات جديدة
        long_signal, long_level = check_long_signal(df, 1.5)
        if long_signal:
            entry_price = current_price
            equal_low = long_level
            stop_price = equal_low - (df["low"].iloc[-1] * 0.002)
            qty = calc_position_size(balance, entry_price, stop_price, 0.005)
            tp_price = entry_price + (entry_price - stop_price) * 2.0
            trade_manager.open_position("BUY", entry_price, stop_price, tp_price, qty, current_time)
            continue

        short_signal, short_level = check_short_signal(df, 1.5)
        if short_signal:
            entry_price = current_price
            equal_high = short_level
            stop_price = equal_high + (df["high"].iloc[-1] * 0.002)
            qty = calc_position_size(balance, entry_price, stop_price, 0.005)
            tp_price = entry_price - (stop_price - entry_price) * 2.0
            trade_manager.open_position("SELL", entry_price, stop_price, tp_price, qty, current_time)
            continue

    # طباعة النتائج
    stats = trade_manager.get_statistics()
    
    print(f"{'='*70}")
    print(f"📊 نتائج الاختبار الموسع")
    print(f"{'='*70}")
    print(f"إجمالي الصفقات: {stats['total_trades']}")
    print(f"الصفقات الرابحة: {stats['win_count']} ✅")
    print(f"الصفقات الخاسرة: {stats['loss_count']} ❌")
    print(f"نسبة النجاح: {stats['win_rate']:.2f}%")
    print(f"إجمالي الأرباح: ${stats['total_profit']:.2f}")
    print(f"إجمالي الخسائر: ${stats['total_loss']:.2f}")
    print(f"صافي الربح: ${stats['net_profit']:.2f}")
    print(f"متوسط الربح/الصفقة: ${stats['avg_profit']:.2f}")
    print(f"{'='*70}\n")
    
    # طباعة أفضل وأسوأ صفقات
    if trade_manager.closed_trades:
        best_trade = max(trade_manager.closed_trades, key=lambda x: x['pnl'])
        worst_trade = min(trade_manager.closed_trades, key=lambda x: x['pnl'])
        
        print(f"🏆 أفضل صفقة: ${best_trade['pnl']:.2f} ({best_trade['side']})")
        print(f"💔 أسوأ صفقة: ${worst_trade['pnl']:.2f} ({worst_trade['side']})")
        print(f"{'='*70}\n")


if __name__ == "__main__":
    run_fast_backtest(iterations=500)
