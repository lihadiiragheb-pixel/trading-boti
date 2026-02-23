import os
import time
import numpy as np
import pandas as pd
from datetime import datetime
from typing import Optional, Tuple, Dict
import logging

from telegram_notifier import send_telegram_message
from binance_client_manager import BinanceClientManager
from ai_engine import AIEngine

logger = logging.getLogger(__name__)

def calculate_sma(df: pd.DataFrame, window: int = 20) -> pd.Series:
    return df["close"].rolling(window=window).mean()

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
        self.trailing_trigger_pct = 0.01
        self.trailing_offset_pct = 0.005
        self.daily_profit_target = 0.05
        self.daily_loss_limit = 0.02
        self.current_day = datetime.now().day
        self.today_profit = 0.0
        self.today_loss = 0.0

    def _reset_daily_stats(self):
        if datetime.now().day != self.current_day:
            self.current_day = datetime.now().day
            self.today_profit = 0.0
            self.today_loss = 0.0
            logger.info("Daily stats reset.")

    def set_pending_retest(self, side: str, level: float, timestamp: float):
        self._reset_daily_stats()
        if self.today_profit >= self.daily_profit_target or self.today_loss >= self.daily_loss_limit:
            logger.warning("Daily profit target or loss limit reached. Skipping new pending retest.")
            send_telegram_message(self.tg_token, self.tg_chat_id, "⚠️ *تنبيه المخاطر*: تم الوصول إلى حد الربح/الخسارة اليومي. لن يتم فتح صفقات جديدة اليوم.")
            return

        self.pending_retest = {
            "side": side,
            "level": level,
            "timestamp": timestamp,
            "expiry": timestamp + 7200
        }
        msg = f"🔍 *رصد كسر للمستوى ({side})*\n📏 المستوى: {level:.2f}\n⏳ بانتظار إعادة الاختبار (Retest)..."
        send_telegram_message(self.tg_token, self.tg_chat_id, msg)
        logger.info(f"Pending retest set: {side} at {level:.2f}")

    def open_position(self, side: str, entry_price: float, stop_price: float, 
                     tp_price: float, qty: float, timestamp: float) -> Dict:
        self._reset_daily_stats()
        if self.today_profit >= self.daily_profit_target or self.today_loss >= self.daily_loss_limit:
            logger.warning("Daily profit target or loss limit reached. Skipping opening new position.")
            send_telegram_message(self.tg_token, self.tg_chat_id, "⚠️ *تنبيه المخاطر*: تم الوصول إلى حد الربح/الخسارة اليومي. لن يتم فتح صفقات جديدة اليوم.")
            return None

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
        logger.info(f"Position opened: {side} at {entry_price:.2f}, SL: {stop_price:.2f}, TP: {tp_price:.2f}, Qty: {qty}")
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
                    old_stop = trade["stop_price"]
                    trade["stop_price"] = new_stop
                    if not trade["is_trailing"]:
                        trade["is_trailing"] = True
                        send_telegram_message(self.tg_token, self.tg_chat_id, f"🎯 *تفعيل تتبع الوقف*\nتم تأمين الربح عند: {new_stop:.2f}")
                        logger.info(f"Trailing stop activated for BUY. New stop: {new_stop:.2f}")
                    elif new_stop > old_stop:
                        logger.info(f"Trailing stop updated for BUY. Old stop: {old_stop:.2f}, New stop: {new_stop:.2f}")
        
        elif trade["side"] == "SELL":
            if current_price < trade["lowest_price"]:
                trade["lowest_price"] = current_price
            profit_pct = (trade["entry_price"] - current_price) / trade["entry_price"]
            if profit_pct >= self.trailing_trigger_pct:
                new_stop = current_price * (1 + self.trailing_offset_pct)
                if new_stop < trade["stop_price"]:
                    old_stop = trade["stop_price"]
                    trade["stop_price"] = new_stop
                    if not trade["is_trailing"]:
                        trade["is_trailing"] = True
                        send_telegram_message(self.tg_token, self.tg_chat_id, f"🎯 *تفعيل تتبع الوقف*\nتم تأمين الربح عند: {new_stop:.2f}")
                        logger.info(f"Trailing stop activated for SELL. New stop: {new_stop:.2f}")
                    elif new_stop < old_stop:
                        logger.info(f"Trailing stop updated for SELL. Old stop: {old_stop:.2f}, New stop: {new_stop:.2f}")

    def _close_trade(self, exit_price: float, timestamp: float, reason: str, pnl: float) -> Dict:
        trade = self.open_trade.copy()
        trade["exit_price"] = exit_price
        trade["exit_time"] = timestamp
        trade["reason"] = reason
        trade["pnl"] = pnl
        trade["status"] = "CLOSED"
        self.closed_trades.append(trade)
        status_emoji = "✅" if pnl > 0 else "❌"
        side = trade["side"]
        msg = f"{status_emoji} *إغلاق صفقة ({side})*\n📝 السبب: {reason}\n📉 السعر: {exit_price:.2f}\n💵 الربح/الخسارة: {pnl:.2f}$"
        send_telegram_message(self.tg_token, self.tg_chat_id, msg)
        logger.info(f"Trade closed: {side} at {exit_price:.2f}, PnL: {pnl:.2f}, Reason: {reason}")
        if pnl > 0:
            self.total_profit += pnl
            self.win_count += 1
            self.today_profit += pnl
        else:
            self.total_loss += abs(pnl)
            self.loss_count += 1
            self.today_loss += abs(pnl)
        self.open_trade = None
        return trade

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

def check_breakout_signal(df: pd.DataFrame, volume_mult: float = 1.5, market_sentiment: str = "neutral") -> Tuple[bool, str, Optional[float]]:
    if df.empty:
        return False, "", None

    df["SMA"] = calculate_sma(df, window=20)
    if df["SMA"].isnull().any():
        return False, "", None

    current_price = df["close"].iloc[-1]
    current_sma = df["SMA"].iloc[-1]

    equal_lows = detect_equal_lows(df)
    if len(equal_lows) >= 1:
        last_equal = equal_lows.iloc[-1]
        avg_volume = df["volume"].rolling(20).mean().iloc[-1] if len(df) >= 20 else df["volume"].mean()

        if current_price > current_sma and df["low"].iloc[-1] < last_equal and df["volume"].iloc[-1] > avg_volume * volume_mult:
            if market_sentiment == "bearish":
                return False, "", None
            return True, "BUY", last_equal
            
    equal_highs = detect_equal_highs(df)
    if len(equal_highs) >= 1:
        last_equal = equal_highs.iloc[-1]
        avg_volume = df["volume"].rolling(20).mean().iloc[-1] if len(df) >= 20 else df["volume"].mean()

        if current_price < current_sma and df["high"].iloc[-1] > last_equal and df["volume"].iloc[-1] > avg_volume * volume_mult:
            if market_sentiment == "bullish":
                return False, "", None
            return True, "SELL", last_equal
            
    return False, "", None

def calc_position_size(balance: float, entry_price: float, stop_price: float, risk_pct: float = 0.01) -> float:
    if stop_price == entry_price:
        return 0.0
    risk_amount = balance * risk_pct
    risk_per_unit = abs(entry_price - stop_price)
    return round(risk_amount / risk_per_unit, 6) if risk_per_unit != 0 else 0.0

class EqualLevelsBot:
    def __init__(self, symbol: str = "BTCUSDT", timeframe: str = "5m", 
                 rr_ratio: float = 2.0, volume_mult: float = 1.5, 
                 risk_pct: float = 0.01, lookback: int = 50,
                 api_key: str = "", api_secret: str = "",
                 tg_token: str = "", tg_chat_id: str = "",
                 openai_api_key: str = ""):
        self.symbol = symbol
        self.timeframe = timeframe
        self.rr_ratio = rr_ratio
        self.volume_mult = volume_mult
        self.risk_pct = risk_pct
        self.lookback = lookback
        self.client_manager = BinanceClientManager(api_key, api_secret)
        self.trade_manager = TradeManager(tg_token, tg_chat_id)
        self.ai_engine = AIEngine()
        logger.info(f"Bot initialized for {symbol} on {timeframe}")

    def _fetch_market_news(self) -> str:
        news_options = [
            "Bitcoin price surges after positive regulatory news.",
            "Cryptocurrency market experiences sharp decline due to inflation fears.",
            "Major exchange announces new altcoin listing, boosting market confidence.",
            "Global economic uncertainty leads to cautious trading in crypto.",
            "New decentralized finance (DeFi) project gains traction, positive outlook."
        ]
        return np.random.choice(news_options)

    def run_iteration(self):
        self.trade_manager._reset_daily_stats()

        if self.trade_manager.today_loss >= self.trade_manager.daily_loss_limit:
            return
        if self.trade_manager.today_profit >= self.trade_manager.daily_profit_target:
            return

        df = self.client_manager.get_klines(self.symbol, self.timeframe, self.lookback)
        if df is None or df.empty:
            return

        current_price = df["close"].iloc[-1]
        current_time = datetime.now().timestamp()

        if self.trade_manager.open_trade:
            self.trade_manager.check_close_conditions(current_price, current_time)
            return

        pending = self.trade_manager.pending_retest
        if pending:
            market_news = self._fetch_market_news()
            market_sentiment = self.ai_engine.get_market_sentiment(market_news)
            
            side = pending["side"]
            if side == "BUY" and market_sentiment == "bearish":
                self.trade_manager.pending_retest = None
                return
            elif side == "SELL" and market_sentiment == "bullish":
                self.trade_manager.pending_retest = None
                return

            if current_price <= pending["level"] * 1.002 and current_price >= pending["level"] * 0.998:
                balance = self.client_manager.get_balance()
                if side == "BUY":
                    stop = pending["level"] - (current_price * 0.003)
                    tp = current_price + (current_price - stop) * self.rr_ratio
                else:
                    stop = pending["level"] + (current_price * 0.003)
                    tp = current_price - (stop - current_price) * self.rr_ratio
                
                qty = calc_position_size(balance, current_price, stop, self.risk_pct)
                if qty > 0:
                    order_result = self.client_manager.create_order(self.symbol, side, qty)
                    if order_result and order_result.get("status") == "FILLED":
                        self.trade_manager.open_position(side, current_price, stop, tp, qty, current_time)
            return

        market_news = self._fetch_market_news()
        market_sentiment = self.ai_engine.get_market_sentiment(market_news)
        has_signal, side, level = check_breakout_signal(df, self.volume_mult, market_sentiment)
        if has_signal:
            self.trade_manager.set_pending_retest(side, level, current_time)
