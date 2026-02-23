import os
import pandas as pd
import numpy as np
from datetime import datetime
from binance.client import Client
from binance.enums import *
import logging

logger = logging.getLogger(__name__)

class BinanceClientManager:
    def __init__(self, api_key: str = "", api_secret: str = ""):
        self.api_key = api_key
        self.api_secret = api_secret
        if api_key and api_secret:
            self.client = Client(api_key, api_secret)
            logger.info("✅ تم الاتصال ببايننس بنجاح (حساب حقيقي)")
        else:
            self.client = None
            logger.warning("⚠️ لم يتم توفير مفاتيح API، البوت سيعمل في وضع المحاكاة فقط")

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
            logger.error(f"❌ خطأ في جلب البيانات من بينانس: {e}")
            return None

    def get_historical_klines(self, symbol, interval, start_str, end_str=None):
        if not self.client:
            logger.warning("⚠️ لا يمكن جلب بيانات تاريخية حقيقية بدون مفاتيح API. استخدام بيانات محاكاة.")
            # Fallback to simulated data if no API keys for historical data
            return self._get_simulated_klines(500) # Return a reasonable amount of simulated data

        try:
            data = self.client.get_historical_klines(symbol, interval, start_str, end_str)
            df = pd.DataFrame(data, columns=[
                "open_time", "open", "high", "low", "close",
                "volume", "close_time", "qav", "trades", "bav", "qbv", "ignore"
            ])
            for col in ["open", "high", "low", "close", "volume"]:
                df[col] = df[col].astype(float)
            df["open_time"] = pd.to_datetime(df["open_time"], unit="ms")
            df["close_time"] = pd.to_datetime(df["close_time"], unit="ms")
            return df
        except Exception as e:
            logger.error(f"❌ خطأ في جلب البيانات التاريخية من بينانس: {e}")
            return None

    def _get_simulated_klines(self, limit):
        # Improved simulated klines for better backtesting
        data = []
        current_price = 50000.0
        for i in range(limit):
            timestamp = int((datetime.now().timestamp() - (limit - i) * 300) * 1000) # 5m intervals
            open_price = current_price + np.random.uniform(-100, 100)
            close_price = open_price + np.random.uniform(-50, 50)
            high_price = max(open_price, close_price) + np.random.uniform(0, 50)
            low_price = min(open_price, close_price) - np.random.uniform(0, 50)
            volume = np.random.uniform(100, 1000)
            data.append([timestamp, str(open_price), str(high_price), str(low_price), str(close_price), str(volume), 0, "0", 0, "0", "0", "0"])
            current_price = close_price # Update current price for next candle
        
        df = pd.DataFrame(data, columns=["open_time", "open", "high", "low", "close", "volume", "close_time", "qav", "trades", "bav", "qbv", "ignore"])
        for col in ["open", "high", "low", "close", "volume"]:
            df[col] = df[col].astype(float)
        return df

    def get_balance(self, asset="USDT"):
        if not self.client:
            return 1000.0 # Simulated balance
        try:
            return float(self.client.get_asset_balance(asset=asset)["free"])
        except Exception as e:
            logger.error(f"❌ خطأ في جلب الرصيد من بينانس: {e}")
            return 0.0

    def create_order(self, symbol, side, qty):
        if not self.client:
            logger.info(f"✅ أمر محاكاة: {side} {qty} {symbol}")
            return {"orderId": "SIM_" + str(int(datetime.now().timestamp())), "status": "FILLED"}
        try:
            side_type = SIDE_BUY if side == "BUY" else SIDE_SELL
            order = self.client.create_order(
                symbol=symbol,
                side=side_type,
                type=ORDER_TYPE_MARKET,
                quantity=qty
            )
            logger.info(f"✅ تم تنفيذ الأمر: {side} {qty} {symbol} - {order['orderId']}")
            return order
        except Exception as e:
            logger.error(f"❌ فشل تنفيذ الأمر على بينانس: {e}")
            return None
