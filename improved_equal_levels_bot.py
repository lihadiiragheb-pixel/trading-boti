"""
تحسين بوت Equal Lows/Highs - نسخة محسّنة مع إدارة صفقات كاملة
Improved Equal Lows/Highs Bot with Real Binance, Telegram, Trailing Stop, Retest & 5m Timeframe
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
            timestamp = int((datetime.now().timestamp() - (limit - i) * 300) * 1000) # 5m intervals
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

# ===== Trade Manager Class with Trailing & Retest Support =====
class TradeManager:
    def __init__(self, tg_token: str = "", tg_chat_id: str = ""):
        self.open_trade: Optional[Dict] = None
        self.pending_retest: Optional[Dict] = None
        self.closed_trades = []
        self.total_profit = 0
        self.total_loss = 0
        self.win_count = 0
        self.loss_count = 0
        self.tg_token = tg_token
        self.tg_chat_id = tg_chat_id
        # إعدادات تتبع الوقف (Trailing)
        self.trailing_trigger_pct = 0.01  # تفعيل عند ربح 1%
        self.trailing_offset_pct = 0.005  # الحفاظ على مسافة 0.5% من السعر الحالي

    def set_pending_retest(self, side: str, level: float, timestamp: float):
        self.pending_retest = {
            "side": side,
            "level": level,
            "timestamp": timestamp,
            "expiry": timestamp + 7200 # الإشارة صالحة لمدة ساعتين (لأننا على فريم 5 دقائق)
        }
        msg = f"🔍 *رصد كسر للمستوى ({side})*\n📏 المستوى: {level:.2f}\n⏳ بانتظار إعادة الاختبار (Retest)..."
        send_telegram_message(self.tg_token, self.tg_chat_id, msg)

    def open_position(self, side: str, entry_price: float, stop_price: float, 
                     tp_price: float, qty: float, timestamp: float) -> Dict:
        self.open_trade = {
            "side": side,
            "entry_price": entry_price,
            "stop_price": stop_price,
            "initial_stop": stop_price,
            "tp_price": tp_price,
            "qty": qty,
            "entry_time": timestamp,
            "status": "OPEN",
            "is_trailing": False,
            "highest_price": entry_price if side == "BUY" else 999999999,
            "lowest_price": entry_price if side == "SELL" else 0
        }
        self.pending_retest = None
        msg = f"🚀 *تم تأكيد إعادة الاختبار - فتح صفقة ({side})*\n💰 السعر: {entry_price:.2f}\n🛑 الوقف: {stop_price:.2f}\n🎯 الهدف: {tp_price:.2f}\n📦 الكمية: {qty}"
        send_telegram_message(self.tg_token, self.tg_chat_id, msg)
        return self.open_trade

    def check_close_conditions(self, current_price: float, timestamp: float) -> Optional[Dict]:
        if not self.open_trade:
            return None

        trade = self.open_trade
        closed_trade = None
        self._update_trailing_stop(current_price)

        if trade["side"] == "BUY":
            if current_price <= trade["stop_price"]:
                pnl = (current_price - trade["entry_price"]) * trade["qty"]
                closed_trade = self._close_trade(current_price, timestamp, "STOP_LOSS/TRAILING", pnl)
            elif current_price >= trade["tp_price"] and not trade["is_trailing"]:
                pnl = (current_price - trade["entry_price"]) * trade["qty"]
                closed_trade = self._close_trade(current_price, timestamp, "TAKE_PROFIT", pnl)
        
        elif trade["side"] == "SELL":
            if current_price >= trade["stop_price"]:
                pnl = (trade["entry_price"] - current_price) * trade["qty"]
                closed_trade = self._close_trade(current_price, timestamp, "STOP_LOSS/TRAILING", pnl)
            elif current_price <= trade["tp_price"] and not trade["is_trailing"]:
                pnl = (trade["entry_price"] - current_price) * trade["qty"]
                closed_trade = self._close_trade(current_price, timestamp, "TAKE_PROFIT", pnl)

        return closed_trade

    def _update_trailing_stop(self, current_price: float):
        trade = self.open_trade
        if not trade: return

        if trade["side"] == "BUY":
            if current_price > trade["highest_price"]:
                trade["highest_price"] = current_price
            profit_pct = (current_price - trade["entry_price"]) / trade["entry_price"]
            if profit_pct >= self.trailing_trigger_pct:
                new_stop = current_price * (1 - self.trailing_offset_pct)
                if new_stop > trade["stop_price"]:
                    trade["stop_price"] = new_stop
                    if not trade["is_trailing"]:
                        trade["is_trailing"] = True
                        send_telegram_message(self.tg_token, self.tg_chat_id, f"🎯 *تفعيل تتبع الوقف*\nتم تأمين الربح عند: {new_stop:.2f}")
        
        elif trade["side"] == "SELL":
            if current_price < trade["lowest_price"]:
                trade["lowest_price"] = current_price
            profit_pct = (trade["entry_price"] - current_price) / trade["entry_price"]
            if profit_pct >= self.trailing_trigger_pct:
                new_stop = current_price * (1 + self.trailing_offset_pct)
                if new_stop < trade["stop_price"]:
                    trade["stop_price"] = new_stop
                    if not trade["is_trailing"]:
                        trade["is_trailing"] = True
                        send_telegram_message(self.tg_token, self.tg_chat_id, f"🎯 *تفعيل تتبع الوقف*\nتم تأمين الربح عند: {new_stop:.2f}")

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

def check_breakout_signal(df: pd.DataFrame, volume_mult: float = 1.5) -> Tuple[bool, str, Optional[float]]:
    equal_lows = detect_equal_lows(df)
    if len(equal_lows) >= 1:
        last_equal = equal_lows.iloc[-1]
        avg_volume = df["volume"].rolling(20).mean().iloc[-1]
        if df["low"].iloc[-1] < last_equal and df["volume"].iloc[-1] > avg_volume * volume_mult:
            return True, "BUY", last_equal
            
    equal_highs = detect_equal_highs(df)
    if len(equal_highs) >= 1:
        last_equal = equal_highs.iloc[-1]
        avg_volume = df["volume"].rolling(20).mean().iloc[-1]
        if df["high"].iloc[-1] > last_equal and df["volume"].iloc[-1] > avg_volume * volume_mult:
            return True, "SELL", last_equal
            
    return False, "", None

def calc_position_size(balance: float, entry_price: float, stop_price: float, risk_pct: float = 0.01) -> float:
    risk_amount = balance * risk_pct
    risk_per_unit = abs(entry_price - stop_price)
    if risk_per_unit == 0: return 0
    return round(risk_amount / risk_per_unit, 6)

# ===== Main Bot Class =====
class EqualLevelsBot:
    def __init__(self, symbol: str = "BTCUSDT", timeframe: str = "5m", 
                 rr_ratio: float = 2.0, volume_mult: float = 1.5, 
                 risk_pct: float = 0.01, lookback: int = 50,
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

    def run_iteration(self):
        df = self.client_manager.get_klines(self.symbol, self.timeframe, self.lookback)
        if df is None: return

        current_price = df["close"].iloc[-1]
        current_time = datetime.now().timestamp()

        if self.trade_manager.open_trade:
            self.trade_manager.check_close_conditions(current_price, current_time)
            return

        pending = self.trade_manager.pending_retest
        if pending:
            if current_time > pending["expiry"]:
                self.trade_manager.pending_retest = None
                return

            if pending["side"] == "BUY":
                if current_price <= pending["level"] * 1.002 and current_price >= pending["level"] * 0.998:
                    stop = pending["level"] - (current_price * 0.003) # Slightly wider stop for 5m
                    balance = self.client_manager.get_balance()
                    qty = calc_position_size(balance, current_price, stop, self.risk_pct)
                    tp = current_price + (current_price - stop) * self.rr_ratio
                    if self.client_manager.create_order(self.symbol, "BUY", qty):
                        self.trade_manager.open_position("BUY", current_price, stop, tp, qty, current_time)
            
            elif pending["side"] == "SELL":
                if current_price >= pending["level"] * 0.998 and current_price <= pending["level"] * 1.002:
                    stop = pending["level"] + (current_price * 0.003)
                    balance = self.client_manager.get_balance()
                    qty = calc_position_size(balance, current_price, stop, self.risk_pct)
                    tp = current_price - (stop - current_price) * self.rr_ratio
                    if self.client_manager.create_order(self.symbol, "SELL", qty):
                        self.trade_manager.open_position("SELL", current_price, stop, tp, qty, current_time)
            return

        has_signal, side, level = check_breakout_signal(df, self.volume_mult)
        if has_signal:
            self.trade_manager.set_pending_retest(side, level, current_time)
