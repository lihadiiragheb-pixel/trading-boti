"""
تشغيل البوت على MEXC (صفر عمولة) - نسخة فريم الدقيقة (1m)
Bot Runner for MEXC with Telegram & 1m Timeframe
"""

import os
import time
import logging
from datetime import datetime
from improved_equal_levels_bot_mexc import EqualLevelsBotMEXC, send_telegram_message

# إعداد السجلات (Logging)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def main():
    logger.info("="*70)
    logger.info("🤖 بدء تشغيل البوت على MEXC (صفر عمولة)")
    logger.info("="*70)
    
    # الحصول على متغيرات البيئة
    api_key = os.getenv("MEXC_API_KEY", "")
    api_secret = os.getenv("MEXC_API_SECRET", "")
    tg_token = os.getenv("TELEGRAM_BOT_TOKEN", "")
    tg_chat_id = os.getenv("TELEGRAM_CHAT_ID", "")
    symbol = os.getenv("SYMBOL", "BTC/USDT")
    timeframe = os.getenv("TIMEFRAME", "1m") # تم الضبط على فريم الدقيقة بناءً على المحاكاة الرابحة
    rr_ratio = float(os.getenv("RR_RATIO", "2.0"))
    volume_mult = float(os.getenv("VOLUME_MULT", "1.5"))
    risk_pct = float(os.getenv("RISK_PCT", "0.01"))
    lookback = int(os.getenv("LOOKBACK", "50"))
    
    # إرسال إشعار بدء التشغيل لتلجرام
    if tg_token and tg_chat_id:
        mode = "حقيقي ✅ (MEXC)" if api_key else "تجريبي (محاكاة) 🧪"
        start_msg = f"🤖 *تم بدء تشغيل البوت على MEXC*\n📈 الزوج: {symbol}\n⏰ الإطار: {timeframe}\n⚙️ الوضع: {mode}\n💰 المخاطرة: {risk_pct*100}%"
        send_telegram_message(tg_token, tg_chat_id, start_msg)

    # إنشاء البوت
    try:
        bot = EqualLevelsBotMEXC(
            symbol=symbol,
            timeframe=timeframe,
            rr_ratio=rr_ratio,
            volume_mult=volume_mult,
            risk_pct=risk_pct,
            lookback=lookback,
            api_key=api_key,
            api_secret=api_secret,
            tg_token=tg_token,
            tg_chat_id=tg_chat_id
        )
        logger.info("✅ تم بناء محرك البوت بنجاح")
    except Exception as e:
        logger.error(f"❌ خطأ في إنشاء البوت: {e}")
        if tg_token and tg_chat_id:
            send_telegram_message(tg_token, tg_chat_id, f"❌ *خطأ حرج عند بدء البوت:*\n`{str(e)}`")
        return

    # حلقة التشغيل اللانهائية
    iteration = 0
    while True:
        try:
            iteration += 1
            bot.run_iteration()
            # الانتظار لمدة دقيقة واحدة (لأننا على فريم 1m)
            time.sleep(60)
            
        except KeyboardInterrupt:
            logger.info("⛔ تم إيقاف البوت يدوياً")
            break
        except Exception as e:
            logger.error(f"❌ خطأ في الدورة #{iteration}: {e}")
            time.sleep(30)

if __name__ == "__main__":
    main()
