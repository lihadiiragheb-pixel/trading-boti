"""
تحسين بوت Equal Lows/Highs - نسخة MEXC (صفر عمولة)
Improved Equal Lows/Highs Bot for MEXC (Zero Fees) using CCXT
"""

import os
import time
import requests
import numpy as np
import pandas as pd
from datetime import datetime
from typing import Optional, Tuple, Dict
import ccxt

# ===== Telegram Notification Setup =====
def send_telegram_message(token: str, chat_id: str, message: str):
    if not token or not chat_id:
        return
    try:
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        payload = {"chat_id": chat_id, "text": message, "parse_mode": "Markdown"}
        requests.post(url, json=payload)
    except Exception as e:
        print(f"❌ خطأ في إرسال إشعار تلجرام: {e}")

# ===== MEXC Client Setup using CCXT =====
class MEXCClientManager:
    def __init__(self, api_key: str = "", api_secret: str = ""):
        self.api_key = api_key
        self.api_secret = api_secret
        if api_key and api_secret:
            self.exchange = ccxt.mexc({
                'apiKey': api_key,
                'secret': api_secret,
                'enableRateLimit': True,
            })
            print("✅ تم الاتصال بـ MEXC بنجاح (حساب حقيقي)")
        else:
            self.exchange = None
            print("⚠️ لم يتم توفير مفاتيح API، البوت سيعمل في وضع المحاكاة فقط")

    def get_klines(self, symbol, timeframe, limit=100):
        if not self.exchange:
            return self._get_simulated_klines(limit)
        
        try:
            # Convert symbol format if needed (e.g., BTCUSDT -> BTC/USDT)
            if '/' not in symbol:
                symbol = f"{symbol[:-4]}/{symbol[-4:]}"
            
            ohlcv = self.exchange.fetch_ohlcv(symbol, timeframe, limit=limit)
            df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            return df
        except Exception as e:
            print(f"❌ خطأ في جلب البيانات من MEXC: {e}")
            return None

    def _get_simulated_klines(self, limit):
        data = []
        current_price = 50000
        for i in range(limit):
            timestamp = int((datetime.now().timestamp() - (limit - i) * 300) * 1000)
            open_price = current_price + np.random.uniform(-100, 100)
            close_price = open_price + np.random.uniform(-50, 50)
            high_price = max(open_price, close_price) + np.random.uniform(0, 50)
            low_price = min(open_price, close_price) - np.random.uniform(0, 50)
            data.append([timestamp, open_price, high_price, low_price, close_price, 100.0])
        
        df = pd.DataFrame(data, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        return df

    def get_balance(self, asset="USDT"):
        if not self.exchange:
            return 100.0
        try:
            balance = self.exchange.fetch_balance()
            return float(balance['free'][asset])
        except Exception as e:
            print(f"❌ خطأ في جلب الرصيد: {e}")
            return 0.0

    def create_order(self, symbol, side, qty):
        if not self.exchange:
            return {"id": "SIM_123", "status": "closed"}
        try:
            if '/' not in symbol:
                symbol = f"{symbol[:-4]}/{symbol[-4:]}"
            
            order_type = 'market'
            return self.exchange.create_order(symbol, order_type, side.lower(), qty)
        except Exception as e:
            print(f"❌ فشل تنفيذ الأمر على MEXC: {e}")
            return None

# ===== Trade Manager Class =====
class TradeManager:
    def __init__(self, tg_token: str = "", tg_chat_id: str = ""):
        self.open_trade: Optional[Dict] = None
        self.pending_retest: Optional[Dict] = None
        self.tg_token = tg_token
        self.tg_chat_id = tg_chat_id
        self.trailing_trigger_pct = 0.01
        self.trailing_offset_pct = 0.005

    def set_pending_retest(self, side: str, level: float, timestamp: float):
        self.pending_retest = {
            "side": side,
            "level": level,
            "timestamp": timestamp,
            "expiry": timestamp + 7200
        }
        msg = f"🔍 *MEXC: رصد كسر للمستوى ({side})*\n📏 المستوى: {level:.2f}\n⏳ بانتظار إعادة الاختبار..."
        send_telegram_message(self.tg_token, self.tg_chat_id, msg)

    def open_position(self, side: str, entry_price: float, stop_price: float, 
                     tp_price: float, qty: float, timestamp: float) -> Dict:
        self.open_trade = {
            "side": side,
            "entry_price": entry_price,
            "stop_price": stop_price,
            "tp_price": tp_price,
            "qty": qty,
            "entry_time": timestamp,
            "status": "OPEN",
            "is_trailing": False,
            "highest_price": entry_price if side == "BUY" else 999999999
        }
        self.pending_retest = None
        msg = f"🚀 *MEXC: فتح صفقة ({side})*\n💰 السعر: {entry_price:.2f}\n🛑 الوقف: {stop_price:.2f}\n🎯 الهدف: {tp_price:.2f}"
        send_telegram_message(self.tg_token, self.tg_chat_id, msg)
        return self.open_trade

    def check_close_conditions(self, current_price: float, timestamp: float) -> Optional[Dict]:
        if not self.open_trade:
            return None

        trade = self.open_trade
        closed_trade = None

        if trade["side"] == "BUY":
            if current_price <= trade["stop_price"]:
                closed_trade = self._close_trade(current_price, timestamp, "STOP_LOSS")
            elif current_price >= trade["tp_price"]:
                closed_trade = self._close_trade(current_price, timestamp, "TAKE_PROFIT")
        
        return closed_trade

    def _close_trade(self, exit_price: float, timestamp: float, reason: str) -> Dict:
        trade = self.open_trade.copy()
        pnl = (exit_price - trade["entry_price"]) * trade["qty"] if trade["side"] == "BUY" else (trade["entry_price"] - exit_price) * trade["qty"]
        status_emoji = "✅" if pnl > 0 else "❌"
        msg = f"{status_emoji} *MEXC: إغلاق صفقة*\n📝 السبب: {reason}\n📉 السعر: {exit_price:.2f}\n💵 الربح/الخسارة: {pnl:.2f}$"
        send_telegram_message(self.tg_token, self.tg_chat_id, msg)
        self.open_trade = None
        return trade

# ===== Strategy Logic with RSI Filter =====
def calculate_rsi(series, period=14):
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

def detect_equal_lows(df: pd.DataFrame) -> pd.Series:
    return df["low"].rolling(3).agg(lambda x: x.iloc[1] if x.iloc[1] == x.min() else np.nan).dropna()

def check_breakout_signal(df: pd.DataFrame, volume_mult: float = 1.5) -> Tuple[bool, str, Optional[float]]:
    equal_lows = detect_equal_lows(df)
    if len(equal_lows) >= 1:
        last_equal = equal_lows.iloc[-1]
        avg_volume = df["volume"].rolling(20).mean().iloc[-1]
        if df["low"].iloc[-1] < last_equal and df["volume"].iloc[-1] > avg_volume * volume_mult:
            return True, "BUY", last_equal
    return False, "", None

# ===== Main Bot Class =====
class EqualLevelsBotMEXC:
    def __init__(self, symbol: str = "BTCUSDT", timeframe: str = "5m", 
                 rr_ratio: float = 2.0, volume_mult: float = 1.5, 
                 risk_pct: float = 0.01, lookback: int = 100,
                 api_key: str = "", api_secret: str = "",
                 tg_token: str = "", tg_chat_id: str = ""):
        self.symbol = symbol
        self.timeframe = timeframe
        self.rr_ratio = rr_ratio
        self.volume_mult = volume_mult
        self.risk_pct = risk_pct
        self.lookback = lookback
        self.client_manager = MEXCClientManager(api_key, api_secret)
        self.trade_manager = TradeManager(tg_token, tg_chat_id)

    def run_iteration(self):
        df = self.client_manager.get_klines(self.symbol, self.timeframe, self.lookback)
        if df is None or len(df) < 20: return

        df['rsi'] = calculate_rsi(df['close'], 14)
        current_price = df["close"].iloc[-1]
        current_rsi = df["rsi"].iloc[-1]
        current_time = datetime.now().timestamp()

        if self.trade_manager.open_trade:
            self.trade_manager.check_close_conditions(current_price, current_time)
            return

        pending = self.trade_manager.pending_retest
        if pending:
            if current_time > pending["expiry"]:
                self.trade_manager.pending_retest = None
                return
            
            # Entry with RSI Filter (> 50 for Bullish)
            if current_price <= pending["level"] * 1.002 and current_price >= pending["level"] * 0.998 and current_rsi > 50:
                stop = pending["level"] - (current_price * 0.003)
                balance = self.client_manager.get_balance()
                risk_amount = balance * self.risk_pct
                qty = risk_amount / abs(current_price - stop)
                if qty * current_price > balance: qty = balance / current_price
                tp = current_price + (current_price - stop) * self.rr_ratio
                if self.client_manager.create_order(self.symbol, "BUY", qty):
                    self.trade_manager.open_position("BUY", current_price, stop, tp, qty, current_time)
            return

        has_signal, side, level = check_breakout_signal(df, self.volume_mult)
        if has_signal:
            self.trade_manager.set_pending_retest(side, level, current_time)
