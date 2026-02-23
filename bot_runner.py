import os
import time
import logging
from datetime import datetime

from improved_equal_levels_bot import EqualLevelsBot
from telegram_notifier import send_telegram_message

# إعداد السجلات (Logging)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("bot_log.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def main():
    logger.info("="*70)
    logger.info("🤖 بدء تشغيل البوت على Render")
    logger.info("="*70)
    
    # الحصول على متغيرات البيئة من Render
    api_key = os.getenv("BINANCE_API_KEY", "")
    api_secret = os.getenv("BINANCE_API_SECRET", "")
    tg_token = os.getenv("TELEGRAM_BOT_TOKEN", "")
    tg_chat_id = os.getenv("TELEGRAM_CHAT_ID", "")
    symbol = os.getenv("SYMBOL", "BTCUSDT")
    timeframe = os.getenv("TIMEFRAME", "1m")
    rr_ratio = float(os.getenv("RR_RATIO", "2.0"))
    volume_mult = float(os.getenv("VOLUME_MULT", "1.5"))
    risk_pct = float(os.getenv("RISK_PCT", "0.005"))
    lookback = int(os.getenv("LOOKBACK", "50"))
    openai_api_key = os.getenv("OPENAI_API_KEY") # Get OpenAI API Key

    # التحقق من وجود مفتاح OpenAI API
    if not openai_api_key:
        error_msg = "❌ خطأ حرج: مفتاح OPENAI_API_KEY غير موجود. لا يمكن تشغيل البوت بدون الذكاء الاصطناعي."
        logger.critical(error_msg)
        if tg_token and tg_chat_id:
            send_telegram_message(tg_token, tg_chat_id, error_msg)
        return # إنهاء البرنامج إذا كان المفتاح غير موجود

    # إرسال إشعار بدء التشغيل لتلجرام
    if tg_token and tg_chat_id:
        mode = "حقيقي ✅" if api_key else "تجريبي (محاكاة) 🧪"
        start_msg = f"🤖 *تم بدء تشغيل البوت على Render*\n📈 الزوج: {symbol}\n⏰ الإطار: {timeframe}\n⚙️ الوضع: {mode}"
        send_telegram_message(tg_token, tg_chat_id, start_msg)
    
    # إنشاء البوت
    try:
        bot = EqualLevelsBot(
            symbol=symbol,
            timeframe=timeframe,
            rr_ratio=rr_ratio,
            volume_mult=volume_mult,
            risk_pct=risk_pct,
            lookback=lookback,
            level_window=int(os.getenv("LEVEL_WINDOW", "5")),
            level_tolerance_pct=float(os.getenv("LEVEL_TOLERANCE_PCT", "0.0005")),
            api_key=api_key,
            api_secret=api_secret,
            tg_token=tg_token,
            tg_chat_id=tg_chat_id,
            openai_api_key=openai_api_key # Pass OpenAI API Key
        )
        logger.info("✅ تم بناء محرك البوت بنجاح")
    except Exception as e:
        logger.critical(f"❌ خطأ حرج في إنشاء البوت: {e}")
        if tg_token and tg_chat_id:
            send_telegram_message(tg_token, tg_chat_id, f"❌ *خطأ حرج عند بدء البوت:*\n`{str(e)}`")
        return
    
    # حلقة التشغيل اللانهائية
    iteration = 0
    while True:
        try:
            iteration += 1
            logger.info(f"--- بدء الدورة #{iteration} ---")
            bot.run_iteration()
            logger.info(f"--- انتهاء الدورة #{iteration} ---")
            time.sleep(60)
            
        except KeyboardInterrupt:
            logger.info("⛔ تم إيقاف البوت يدوياً")
            if tg_token and tg_chat_id:
                send_telegram_message(tg_token, tg_chat_id, "⛔ *تم إيقاف البوت يدوياً*")
            bot.trade_manager.save_state() # Save state before exiting
            break
        except Exception as e:
            logger.error(f"❌ خطأ في الدورة #{iteration}: {e}")
            if tg_token and tg_chat_id:
                send_telegram_message(tg_token, tg_chat_id, f"❌ *خطأ في دورة البوت #{iteration}:*\n`{str(e)}`")
            bot.trade_manager.save_state() # Save state before attempting to restart or exit
            time.sleep(30) # انتظار قبل المحاولة مرة أخرى

if __name__ == "__main__":
    main()
