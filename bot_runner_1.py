"""
تشغيل البوت على VPS - مع دعم متغيرات البيئة
Bot Runner for VPS Deployment
"""

import os
import time
import logging
from datetime import datetime

# إعداد السجلات
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# محاولة استيراد البوت
try:
    from improved_equal_levels_bot import EqualLevelsBot
    logger.info("✅ تم تحميل البوت بنجاح")
except ImportError as e:
    logger.error(f"❌ خطأ في تحميل البوت: {e}")
    exit(1)


def main():
    """الدالة الرئيسية لتشغيل البوت"""
    
    logger.info("="*70)
    logger.info("🤖 بدء البوت على VPS")
    logger.info("="*70)
    
    # الحصول على متغيرات البيئة
    api_key = os.getenv("BINANCE_API_KEY", "")
    api_secret = os.getenv("BINANCE_API_SECRET", "")
    
    if not api_key or not api_secret:
        logger.warning("⚠️  لم يتم العثور على مفاتيح Binance API")
        logger.info("استخدام محاكي للاختبار...")
    else:
        logger.info("✅ تم العثور على مفاتيح API")
    
    # إعدادات البوت
    symbol = os.getenv("SYMBOL", "BTCUSDT")
    timeframe = os.getenv("TIMEFRAME", "1m")
    rr_ratio = float(os.getenv("RR_RATIO", "2.0"))
    volume_mult = float(os.getenv("VOLUME_MULT", "1.5"))
    risk_pct = float(os.getenv("RISK_PCT", "0.005"))
    lookback = int(os.getenv("LOOKBACK", "50"))
    
    logger.info(f"إعدادات البوت:")
    logger.info(f"  الرمز: {symbol}")
    logger.info(f"  الإطار الزمني: {timeframe}")
    logger.info(f"  نسبة الربح/الخسارة: {rr_ratio}")
    logger.info(f"  مضاعف الحجم: {volume_mult}")
    logger.info(f"  نسبة المخاطرة: {risk_pct}")
    logger.info(f"  فترة النظر: {lookback}")
    
    # إنشاء البوت
    try:
        bot = EqualLevelsBot(
            symbol=symbol,
            timeframe=timeframe,
            rr_ratio=rr_ratio,
            volume_mult=volume_mult,
            risk_pct=risk_pct,
            lookback=lookback
        )
        logger.info("✅ تم إنشاء البوت بنجاح")
    except Exception as e:
        logger.error(f"❌ خطأ في إنشاء البوت: {e}")
        exit(1)
    
    # تشغيل البوت بشكل مستمر
    iteration_count = 0
    error_count = 0
    max_errors = 10
    
    while True:
        try:
            iteration_count += 1
            logger.info(f"🔄 دورة #{iteration_count} - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            
            # تشغيل دورة واحدة
            bot.run(iterations=100)
            
            # إعادة تعيين عداد الأخطاء عند النجاح
            error_count = 0
            
            # انتظر قبل الدورة التالية
            logger.info("⏳ انتظار 60 ثانية قبل الدورة التالية...")
            time.sleep(60)
            
        except KeyboardInterrupt:
            logger.info("⛔ تم إيقاف البوت بواسطة المستخدم")
            break
            
        except Exception as e:
            error_count += 1
            logger.error(f"❌ خطأ في الدورة #{iteration_count}: {e}")
            logger.error(f"عدد الأخطاء: {error_count}/{max_errors}")
            
            if error_count >= max_errors:
                logger.critical(f"❌ تم الوصول للحد الأقصى من الأخطاء ({max_errors})")
                break
            
            # انتظر قبل إعادة المحاولة
            wait_time = min(60 * error_count, 300)  # أقصى 5 دقائق
            logger.info(f"⏳ انتظار {wait_time} ثانية قبل إعادة المحاولة...")
            time.sleep(wait_time)
    
    logger.info("="*70)
    logger.info("🛑 تم إيقاف البوت")
    logger.info("="*70)


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        logger.critical(f"❌ خطأ حرج: {e}")
        exit(1)
