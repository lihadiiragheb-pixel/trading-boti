"""
اختبار موسع للبوت المحسّن - 1000 تكرار
Extended Test for Improved Bot - 1000 Iterations
"""

import sys
sys.path.insert(0, '/home/ubuntu')

from improved_equal_levels_bot import EqualLevelsBot

if __name__ == "__main__":
    print("\n" + "="*70)
    print("🚀 اختبار موسع للبوت المحسّن - 1000 تكرار (دقيقة)")
    print("="*70 + "\n")
    
    bot = EqualLevelsBot(
        symbol="BTCUSDT",
        timeframe="1m",
        rr_ratio=2.0,
        volume_mult=1.5,
        risk_pct=0.005,
        lookback=50
    )
    
    # تشغيل 1000 تكرار
    bot.run(iterations=1000)
