import os
import logging
import pandas as pd
from openai import OpenAI

logger = logging.getLogger(__name__)

class AIEngine:
    def __init__(self):
        api_key = os.getenv("OPENAI_API_KEY")
        try:
            self.client = OpenAI(api_key=api_key)
            logger.info("✅ تم تهيئة عميل OpenAI بنجاح.")
        except Exception as e:
            logger.critical(f"❌ خطأ حرج في تهيئة عميل OpenAI: {e}")
            raise

    def get_market_sentiment(self, news_headlines: str) -> str:
        try:
            response = self.client.chat.completions.create(
                model="gpt-4.1-mini",
                messages=[
                    {"role": "system", "content": "You are a financial market sentiment analysis expert. Analyze the provided news headlines and determine the overall market sentiment (bullish, bearish, or neutral). Provide only one word as the answer."},
                    {"role": "user", "content": f"Analyze the following news headlines for cryptocurrency market sentiment: {news_headlines}"}
                ],
                temperature=0.2,
                max_tokens=10
            )
            sentiment = response.choices[0].message.content.strip().lower()
            logger.info(f"Market sentiment detected: {sentiment}")
            if sentiment in ["bullish", "bearish", "neutral"]:
                return sentiment
            return "neutral"
        except Exception as e:
            logger.error(f"❌ خطأ في تحليل المشاعر: {e}")
            return "neutral"

    def predict_price_direction(self, historical_data: pd.DataFrame) -> str:
        return "neutral"

    def optimize_parameters(self, market_conditions: str) -> dict:
        return {}
