import os
import time
import numpy as np
import pandas as pd
from datetime import datetime
from typing import Optional, Tuple, Dict
import logging
import json

from telegram_notifier import send_telegram_message
from binance_client_manager import BinanceClientManager
from ai_engine import AIEngine

logger = logging.getLogger(__name__)

def calculate_sma(df: pd.DataFrame, window: int = 20) -> pd.Series:
    return df["close"].rolling(window=window).mean()

def _timeframe_to_seconds(timeframe_str: str) -> int:
    if timeframe_str.endswith("m"):
        return int(timeframe_str[:-1]) * 60
    elif timeframe_str.endswith("h"):
        return int(timeframe_str[:-1]) * 3600
    elif timeframe_str.endswith("d"):
        return int(timeframe_str[:-1]) * 86400
    return 3600 # Default to 1 hour if unknown

class TradeManager:
    def __init__(self, tg_token: str = "", tg_chat_id: str = "", timeframe: str = "1m"):
        self.timeframe = timeframe
        self.open_trade: Optional[Dict] = None
        self.pending_retest: Optional[Dict] = None
        self.closed_trades = []
        self.total_profit = 0.0
        self.total_loss = 0.0
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
        self.state_file = "trade_manager_state.json"
        self.load_state()

    def save_state(self):
        state = {
            "open_trade": self.open_trade,
            "pending_retest": self.pending_retest,
            "closed_trades": self.closed_trades,
            "total_profit": self.total_profit,
            "total_loss": self.total_loss,
            "win_count": self.win_count,
            "loss_count": self.loss_count,
            "daily_profit_target": self.daily_profit_target,
            "daily_loss_limit": self.daily_loss_limit,
            "current_day": self.current_day,
            "today_profit": self.today_profit,
            "today_loss": self.today_loss
        }
        try:
            with open(self.state_file, "w") as f:
                json.dump(state, f)
            logger.debug("TradeManager state saved.")
        except Exception as e:
            logger.error(f"Error saving TradeManager state: {e}")

    def load_state(self):
        if os.path.exists(self.state_file):
            try:
                with open(self.state_file, "r") as f:
                    state = json.load(f)
                self.open_trade = state.get("open_trade")
                self.pending_retest = state.get("pending_retest")
                self.closed_trades = state.get("closed_trades", [])
                self.total_profit = state.get("total_profit", 0.0)
                self.total_loss = state.get("total_loss", 0.0)
                self.win_count = state.get("win_count", 0)
                self.loss_count = state.get("loss_count", 0)
                self.daily_profit_target = state.get("daily_profit_target", 0.05)
                self.daily_loss_limit = state.get("daily_loss_limit", 0.02)
                self.current_day = state.get("current_day", datetime.now().day)
                self.today_profit = state.get("today_profit", 0.0)
                self.today_loss = state.get("today_loss", 0.0)
                logger.info("TradeManager state loaded.")
            except Exception as e:
                logger.error(f"Error loading TradeManager state: {e}")
        else:
            logger.info("No TradeManager state file found. Starting fresh.")

    def _reset_daily_stats(self):
        if datetime.now().day != self.current_day:
            self.current_day = datetime.now().day
            self.today_profit = 0.0
            self.today_loss = 0.0
            logger.info("Daily stats reset.")
            self.save_state()

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
            "expiry": timestamp + _timeframe_to_seconds(self.timeframe) * 5 # 5 candles expiry
        }
        msg = f"🔍 *رصد كسر للمستوى ({side})*\n📏 المستوى: {level:.2f}\n⏳ بانتظار إعادة الاختبار (Retest)..."
        send_telegram_message(self.tg_token, self.tg_chat_id, msg)
        logger.info(f"Pending retest set: {side} at {level:.2f}")
        self.save_state()

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
        self.save_state()
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
        self.save_state() # Save state after trailing stop adjustment

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
        self.save_state()
        return trade

def detect_equal_lows(df: pd.DataFrame, window: int = 5, tolerance_pct: float = 0.0005) -> pd.Series:
    if len(df) < window:
        return pd.Series(dtype=float)
    # Find lows that are within the tolerance percentage of the lowest in the window
    lows = df["low"].rolling(window=window).apply(lambda x: x.iloc[window//2] if abs(x.iloc[window//2] - x.min()) / x.iloc[window//2] <= tolerance_pct else np.nan, raw=False)
    return lows.dropna()

def detect_equal_highs(df: pd.DataFrame, window: int = 5, tolerance_pct: float = 0.0005) -> pd.Series:
    if len(df) < window:
        return pd.Series(dtype=float)
    # Find highs that are within the tolerance percentage of the highest in the window
    highs = df["high"].rolling(window=window).apply(lambda x: x.iloc[window//2] if abs(x.iloc[window//2] - x.max()) / x.iloc[window//2] <= tolerance_pct else np.nan, raw=False)
    return highs.dropna()

def check_breakout_signal(df: pd.DataFrame, volume_mult: float = 1.5, market_sentiment: str = "neutral", level_window: int = 5, level_tolerance_pct: float = 0.0005) -> Tuple[bool, str, Optional[float]]:
    if df.empty or len(df) < 50: # Ensure enough data for SMA and levels
        return False, "", None

    df["SMA_50"] = calculate_sma(df, window=50) # Use a longer SMA for better trend filtering
    if df["SMA_50"].isnull().any():
        return False, "", None

    current_price = df["close"].iloc[-1]
    current_sma = df["SMA_50"].iloc[-1]
    current_volume = df["volume"].iloc[-1]
    avg_volume = df["volume"].rolling(50).mean().iloc[-1] # Average volume over a longer period

    # Check for BUY signal
    equal_lows = detect_equal_lows(df, window=level_window, tolerance_pct=level_tolerance_pct)
    if not equal_lows.empty:
        last_equal_low = equal_lows.iloc[-1]
        # Conditions for BUY: Price above SMA, break below equal low, high volume, and not bearish sentiment
        if current_price > current_sma and df["low"].iloc[-1] < last_equal_low and current_volume > avg_volume * volume_mult:
            if market_sentiment == "bearish":
                return False, "", None # Filter out BUY signals if sentiment is bearish
            return True, "BUY", last_equal_low
            
    # Check for SELL signal
    equal_highs = detect_equal_highs(df, window=level_window, tolerance_pct=level_tolerance_pct)
    if not equal_highs.empty:
        last_equal_high = equal_highs.iloc[-1]
        # Conditions for SELL: Price below SMA, break above equal high, high volume, and not bullish sentiment
        if current_price < current_sma and df["high"].iloc[-1] > last_equal_high and current_volume > avg_volume * volume_mult:
            if market_sentiment == "bullish":
                return False, "", None # Filter out SELL signals if sentiment is bullish
            return True, "SELL", last_equal_high
            
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
                 level_window: int = 5, level_tolerance_pct: float = 0.0005,
                 api_key: str = "", api_secret: str = "",
                 tg_token: str = "", tg_chat_id: str = "",
                 openai_api_key: str = ""):
        self.symbol = symbol
        self.timeframe = timeframe
        self.rr_ratio = rr_ratio
        self.volume_mult = volume_mult
        self.risk_pct = risk_pct
        self.lookback = lookback
        self.level_window = level_window
        self.level_tolerance_pct = level_tolerance_pct
        self.client_manager = BinanceClientManager(api_key, api_secret)
        self.trade_manager = TradeManager(tg_token, tg_chat_id, timeframe)
        self.ai_engine = AIEngine()
        logger.info(f"Bot initialized for {symbol} on {timeframe}")

    def _fetch_market_news(self) -> str:
        # TODO: Replace with actual news fetching from a reliable source (e.g., CryptoPanic API, RSS feeds)
        # For now, using simulated news for demonstration purposes.
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
            logger.warning("Daily loss limit reached. Skipping iteration.")
            return

        df = self.client_manager.get_klines(self.symbol, self.timeframe, limit=self.lookback)
        if df is None or df.empty:
            logger.error("Failed to get klines data.")
            return

        current_price = df["close"].iloc[-1]
        # Convert close_time to timestamp (it might be a numpy.int64 or datetime)
        last_close_time = df["close_time"].iloc[-1]
        if isinstance(last_close_time, (int, np.int64)):
            current_time = float(last_close_time) / 1000.0 # Binance timestamps are in ms
        else:
            current_time = last_close_time.timestamp()

        market_news = self._fetch_market_news()
        market_sentiment = self.ai_engine.get_market_sentiment(market_news)
        logger.info(f"Checking for signals with sentiment: {market_sentiment}")
        has_signal, side, level = check_breakout_signal(df, self.volume_mult, market_sentiment, self.level_window, self.level_tolerance_pct)
        if has_signal:
            # Check if there's an existing pending retest for the same level and side
            if self.trade_manager.pending_retest and \
               self.trade_manager.pending_retest["level"] == level and \
               self.trade_manager.pending_retest["side"] == side:
                logger.info(f"Pending retest for {side} at {level:.2f} already exists. Skipping.")
            else:
                self.trade_manager.set_pending_retest(side, level, current_time)

        # Handle pending retest logic
        if self.trade_manager.pending_retest:
            pending_retest = self.trade_manager.pending_retest
            # Check if pending retest has expired
            if current_time > pending_retest["expiry"]:
                logger.info(f"Pending retest for {pending_retest['side']} at {pending_retest['level']:.2f} expired.")
                send_telegram_message(self.trade_manager.tg_token, self.trade_manager.tg_chat_id, f"⏰ *إلغاء إعادة الاختبار*: انتهت صلاحية إعادة اختبار المستوى {pending_retest['level']:.2f} ({pending_retest['side']}).")
                self.trade_manager.pending_retest = None
                self.trade_manager.save_state() # Save state after clearing pending retest
            else:
                # Check sentiment before confirming retest
                if (pending_retest["side"] == "BUY" and market_sentiment == "bearish") or \
                   (pending_retest["side"] == "SELL" and market_sentiment == "bullish"):
                    logger.warning(f"Pending retest for {pending_retest['side']} at {pending_retest['level']:.2f} cancelled due to adverse market sentiment ({market_sentiment}).")
                    send_telegram_message(self.trade_manager.tg_token, self.trade_manager.tg_chat_id, f"🚫 *إلغاء إعادة الاختبار*: تم إلغاء إعادة اختبار المستوى {pending_retest['level']:.2f} ({pending_retest['side']}) بسبب مشاعر السوق السلبية ({market_sentiment}).")
                    self.trade_manager.pending_retest = None
                    self.trade_manager.save_state() # Save state after clearing pending retest
                else:
                    # Check for retest confirmation
                    if pending_retest["side"] == "BUY":
                        # Confirm retest: current price is above the level, but the open of the candle was below
                        if current_price >= pending_retest["level"] and df["open"].iloc[-1] < pending_retest["level"]:
                            entry_price = current_price
                            # Calculate stop loss based on a recent low or a fixed percentage below the level
                            # For simplicity, using a fixed percentage below the level for now
                            stop_price = pending_retest["level"] * (1 - self.risk_pct * self.rr_ratio)
                            tp_price = entry_price + (entry_price - stop_price) * self.rr_ratio
                            balance = self.client_manager.get_balance()
                            qty = calc_position_size(balance, entry_price, stop_price, self.risk_pct)
                            if qty > 0:
                                self.trade_manager.open_position("BUY", entry_price, stop_price, tp_price, qty, current_time)
                            else:
                                logger.warning("Calculated quantity is zero or negative. Not opening BUY position.")

                    elif pending_retest["side"] == "SELL":
                        # Confirm retest: current price is below the level, but the open of the candle was above
                        if current_price <= pending_retest["level"] and df["open"].iloc[-1] > pending_retest["level"]:
                            entry_price = current_price
                            # Calculate stop loss based on a recent high or a fixed percentage above the level
                            # For simplicity, using a fixed percentage above the level for now
                            stop_price = pending_retest["level"] * (1 + self.risk_pct * self.rr_ratio)
                            tp_price = entry_price - (stop_price - entry_price) * self.rr_ratio
                            balance = self.client_manager.get_balance()
                            qty = calc_position_size(balance, entry_price, stop_price, self.risk_pct)
                            if qty > 0:
                                self.trade_manager.open_position("SELL", entry_price, stop_price, tp_price, qty, current_time)
                            else:
                                logger.warning("Calculated quantity is zero or negative. Not opening SELL position.")

        # Check for open trade close conditions
        if self.trade_manager.open_trade:
            self.trade_manager.check_close_conditions(current_price, current_time)
        
        logger.info("Iteration completed successfully.")
        time.sleep(60)
        
if __name__ == "__main__":
    main()
