"""
تحسين بوت Equal Lows/Highs - نسخة محسّنة مع إدارة صفقات كاملة
Improved Equal Lows/Highs Bot with Real Binance & Telegram Integration
"""

import os
import time
import requests
import numpy as np
import pandas as pd
from datetime import datetime
from typing import Optional, Tuple, Dict
from binance.client import Client
from binance.enums import *

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

# ===== Binance Client Setup =====
class BinanceClientManager:
    def __init__(self, api_key: str = "", api_secret: str = ""):
        self.api_key = api_key
        self.api_secret = api_secret
        if api_key and api_secret:
            self.client = Client(api_key, api_secret)
            print("✅ تم الاتصال ببايننس بنجاح (حساب حقيقي)")
        else:
            self.client = None
            print("⚠️ لم يتم توفير مفاتيح API، البوت سيعمل في وضع المحاكاة فقط")

    def get_klines(self, symbol, interval, limit=100):
        if not self.client:
            return self._get_simulated_klines(limit)
        
        try:
            data = self.client.get_klines(symbol=symbol, interval=interval, limit=limit)
            df = pd.DataFrame(data, columns=[
                "open_time", "open", "high", "low", "close",
                "volume", "close_time", "qav", "trades", "bav", "qbv", "ignore"
            ])
            for col in ["open", "high", "low", "close", "volume"]:
                df[col] = df[col].astype(float)
            return df
        except Exception as e:
            print(f"❌ خطأ في جلب البيانات: {e}")
            return None

    def _get_simulated_klines(self, limit):
        data = []
        current_price = 50000
        for i in range(limit):
            timestamp = int((datetime.now().timestamp() - (limit - i) * 60) * 1000)
            open_price = current_price + np.random.uniform(-100, 100)
            close_price = open_price + np.random.uniform(-50, 50)
            high_price = max(open_price, close_price) + np.random.uniform(0, 50)
            low_price = min(open_price, close_price) - np.random.uniform(0, 50)
            data.append([timestamp, str(open_price), str(high_price), str(low_price), str(close_price), "100", 0, "0", 0, "0", "0", "0"])
        
        df = pd.DataFrame(data, columns=["open_time", "open", "high", "low", "close", "volume", "close_time", "qav", "trades", "bav", "qbv", "ignore"])
        for col in ["open", "high", "low", "close", "volume"]:
            df[col] = df[col].astype(float)
        return df

    def get_balance(self, asset="USDT"):
        if not self.client:
            return 1000.0
        try:
            return float(self.client.get_asset_balance(asset=asset)["free"])
        except:
            return 0.0

    def create_order(self, symbol, side, qty):
        if not self.client:
            return {"orderId": "SIM_123", "status": "FILLED"}
        try:
            side_type = SIDE_BUY if side == "BUY" else SIDE_SELL
            return self.client.create_order(
                symbol=symbol,
                side=side_type,
                type=ORDER_TYPE_MARKET,
                quantity=qty
            )
        except Exception as e:
            print(f"❌ فشل تنفيذ الأمر: {e}")
            return None

# ===== Trade Manager Class =====
class TradeManager:
    def __init__(self, tg_token: str = "", tg_chat_id: str = ""):
        self.open_trade: Optional[Dict] = None
        self.closed_trades = []
        self.total_profit = 0
        self.total_loss = 0
        self.win_count = 0
        self.loss_count = 0
        self.tg_token = tg_token
        self.tg_chat_id = tg_chat_id

    def open_position(self, side: str, entry_price: float, stop_price: float, 
                     tp_price: float, qty: float, timestamp: float) -> Dict:
        self.open_trade = {
            "side": side,
            "entry_price": entry_price,
            "stop_price": stop_price,
            "tp_price": tp_price,
            "qty": qty,
            "entry_time": timestamp,
            "status": "OPEN"
        }
        msg = f"🚀 *فتح صفقة جديدة ({side})*\n💰 السعر: {entry_price:.2f}\n🛑 الوقف: {stop_price:.2f}\n🎯 الهدف: {tp_price:.2f}\n📦 الكمية: {qty}"
        send_telegram_message(self.tg_token, self.tg_chat_id, msg)
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
        status_emoji = "✅" if pnl > 0 else "❌"
        msg = f"{status_emoji} *إغلاق صفقة ({trade['side']})*\n📝 السبب: {reason}\n📉 السعر: {exit_price:.2f}\n💵 الربح/الخسارة: {pnl:.2f}$"
        send_telegram_message(self.tg_token, self.tg_chat_id, msg)

        if pnl > 0:
            self.total_profit += pnl
            self.win_count += 1
        else:
            self.total_loss += abs(pnl)
            self.loss_count += 1

        self.open_trade = None
        return trade

# ===== Strategy Logic =====
def detect_equal_lows(df: pd.DataFrame) -> pd.Series:
    lows = df["low"].rolling(3).agg(lambda x: x.iloc[1] if x.iloc[1] == x.min() else np.nan)
    return lows.dropna()

def detect_equal_highs(df: pd.DataFrame) -> pd.Series:
    highs = df["high"].rolling(3).agg(lambda x: x.iloc[1] if x.iloc[1] == x.max() else np.nan)
    return highs.dropna()

def check_long_signal(df: pd.DataFrame, volume_mult: float = 1.5) -> Tuple[bool, Optional[float]]:
    equal_lows = detect_equal_lows(df)
    if len(equal_lows) < 1: return False, None
    last_equal = equal_lows.iloc[-1]
    avg_volume = df["volume"].rolling(20).mean().iloc[-1]
    if df["low"].iloc[-1] < last_equal and df["volume"].iloc[-1] > avg_volume * volume_mult:
        return True, last_equal
    return False, None

def check_short_signal(df: pd.DataFrame, volume_mult: float = 1.5) -> Tuple[bool, Optional[float]]:
    equal_highs = detect_equal_highs(df)
    if len(equal_highs) < 1: return False, None
    last_equal = equal_highs.iloc[-1]
    avg_volume = df["volume"].rolling(20).mean().iloc[-1]
    if df["high"].iloc[-1] > last_equal and df["volume"].iloc[-1] > avg_volume * volume_mult:
        return True, last_equal
    return False, None

def calc_position_size(balance: float, entry_price: float, stop_price: float, risk_pct: float = 0.005) -> float:
    risk_amount = balance * risk_pct
    risk_per_unit = abs(entry_price - stop_price)
    if risk_per_unit == 0: return 0
    return round(risk_amount / risk_per_unit, 6)

# ===== Main Bot Class =====
class EqualLevelsBot:
    def __init__(self, symbol: str = "BTCUSDT", timeframe: str = "1m", 
                 rr_ratio: float = 2.0, volume_mult: float = 1.5, 
                 risk_pct: float = 0.005, lookback: int = 50,
                 api_key: str = "", api_secret: str = "",
                 tg_token: str = "", tg_chat_id: str = ""):
        self.symbol = symbol
        self.timeframe = timeframe
        self.rr_ratio = rr_ratio
        self.volume_mult = volume_mult
        self.risk_pct = risk_pct
        self.lookback = lookback
        self.client_manager = BinanceClientManager(api_key, api_secret)
        self.trade_manager = TradeManager(tg_token, tg_chat_id)
        self.tg_token = tg_token
        self.tg_chat_id = tg_chat_id

    def run_iteration(self):
        df = self.client_manager.get_klines(self.symbol, self.timeframe, self.lookback)
        if df is None: return

        current_price = df["close"].iloc[-1]
        current_time = datetime.now().timestamp()

        if self.trade_manager.open_trade:
            self.trade_manager.check_close_conditions(current_price, current_time)
            return

        long_sig, level = check_long_signal(df, self.volume_mult)
        if long_sig:
            stop = level - (current_price * 0.002)
            balance = self.client_manager.get_balance()
            qty = calc_position_size(balance, current_price, stop, self.risk_pct)
            tp = current_price + (current_price - stop) * self.rr_ratio
            if self.client_manager.create_order(self.symbol, "BUY", qty):
                self.trade_manager.open_position("BUY", current_price, stop, tp, qty, current_time)
            return

        short_sig, level = check_short_signal(df, self.volume_mult)
        if short_sig:
            stop = level + (current_price * 0.002)
            balance = self.client_manager.get_balance()
            qty = calc_position_size(balance, current_price, stop, self.risk_pct)
            tp = current_price - (stop - current_price) * self.rr_ratio
            if self.client_manager.create_order(self.symbol, "SELL", qty):
                self.trade_manager.open_position("SELL", current_price, stop, tp, qty, current_time)
