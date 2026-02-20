"""
تشغيل البوت على Render / VPS - مع دعم كامل لمتغيرات البيئة
Bot Runner for Continuous Execution
"""

import os
import time
import logging
from datetime import datetime
from improved_equal_levels_bot import EqualLevelsBot

# إعداد السجلات (Logging)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def main():
    logger.info("="*70)
    logger.info("🤖 بدء تشغيل البوت على Render")
    logger.info("="*70)
    
    # الحصول على متغيرات البيئة من Render
    api_key = os.getenv("BINANCE_API_KEY", "")
    api_secret = os.getenv("BINANCE_API_SECRET", "")
    symbol = os.getenv("SYMBOL", "BTCUSDT")
    timeframe = os.getenv("TIMEFRAME", "1m")
    rr_ratio = float(os.getenv("RR_RATIO", "2.0"))
    volume_mult = float(os.getenv("VOLUME_MULT", "1.5"))
    risk_pct = float(os.getenv("RISK_PCT", "0.005"))
    lookback = int(os.getenv("LOOKBACK", "50"))
    
    if not api_key or not api_secret:
        logger.warning("⚠️ لم يتم العثور على مفاتيح API في متغيرات البيئة!")
        logger.info("سيتم تشغيل البوت في وضع المحاكاة (Paper Trading)...")
    else:
        logger.info(f"✅ تم العثور على مفاتيح API للزوج: {symbol}")
    
    # إنشاء البوت
    try:
        bot = EqualLevelsBot(
            symbol=symbol,
            timeframe=timeframe,
            rr_ratio=rr_ratio,
            volume_mult=volume_mult,
            risk_pct=risk_pct,
            lookback=lookback,
            api_key=api_key,
            api_secret=api_secret
        )
        logger.info("✅ تم بناء محرك البوت بنجاح")
    except Exception as e:
        logger.error(f"❌ خطأ في إنشاء البوت: {e}")
        return

    # حلقة التشغيل اللانهائية
    iteration = 0
    while True:
        try:
            iteration += 1
            # logger.info(f"🔄 دورة #{iteration} - {datetime.now().strftime('%H:%M:%S')}")
            
            # تشغيل دورة واحدة من الاستراتيجية
            bot.run_iteration()
            
            # الانتظار لمدة دقيقة (أو حسب التايم فريم)
            # بما أن التايم فريم دقيقة، ننتظر 60 ثانية
            time.sleep(60)
            
        except KeyboardInterrupt:
            logger.info("⛔ تم إيقاف البوت يدوياً")
            break
        except Exception as e:
            logger.error(f"❌ خطأ غير متوقع في الدورة #{iteration}: {e}")
            time.sleep(30) # انتظار قصير قبل إعادة المحاولة

if __name__ == "__main__":
    main()
