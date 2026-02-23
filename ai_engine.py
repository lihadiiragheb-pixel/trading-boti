import os
import logging
from openai import OpenAI

logger = logging.getLogger(__name__)

class AIEngine:
    def __init__(self):
        api_key = os.getenv("OPENAI_API_KEY")
        # bot_runner.py already ensures api_key is present, so we can directly initialize
        try:
            self.client = OpenAI(api_key=api_key)
            logger.info("✅ تم تهيئة عميل OpenAI بنجاح.")
        except Exception as e:
            logger.critical(f"❌ خطأ حرج في تهيئة عميل OpenAI: {e}. يرجى التحقق من مفتاح API.")
            # Re-raise the exception as it's a critical failure if bot_runner didn't catch it
            raise

    def get_market_sentiment(self, news_headlines: str) -> str:
        try:
            response = self.client.chat.completions.create(
                model="gpt-4.1-mini", # Using a suitable model for sentiment analysis
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
            else:
                logger.warning(f"Unexpected sentiment response from OpenAI: {sentiment}. Defaulting to neutral.")
                return "neutral"
        except Exception as e:
            logger.error(f"❌ خطأ في تحليل المشاعر باستخدام OpenAI: {e}. العودة إلى المشاعر المحايدة.")
            return "neutral"

    # Placeholder for future price prediction or parameter optimization functions
    def predict_price_direction(self, historical_data: pd.DataFrame) -> str:
        # This would involve training a model or using advanced prompts
        logger.info("Price prediction function is a placeholder.")
        return "neutral"

    def optimize_parameters(self, market_conditions: str) -> dict:
        # This would involve more complex AI logic
        logger.info("Parameter optimization function is a placeholder.")
        return {}
