# 🚀 دليل نشر البوت على VPS سحابي

## **الخطوة 1: اختيار مزود VPS**

### **الخيارات الموصى بها:**

#### **1. Railway (الأفضل للمبتدئين)**
- **الموقع:** https://railway.app
- **السعر:** مجاني (أول $5 شهرياً) أو $5-10 شهرياً
- **المميزات:** سهل جداً، لا يحتاج معرفة تقنية
- **الخطوات:**
  1. اذهب إلى https://railway.app
  2. سجل بحسابك (GitHub أو Google)
  3. اضغط "New Project"
  4. اختر "Deploy from GitHub"
  5. اختر repository يحتوي على البوت

#### **2. Render**
- **الموقع:** https://render.com
- **السعر:** مجاني (مع قيود) أو $7 شهرياً
- **المميزات:** موثوق جداً

#### **3. PythonAnywhere**
- **الموقع:** https://www.pythonanywhere.com
- **السعر:** مجاني أو $5 شهرياً
- **المميزات:** متخصصة في Python

#### **4. DigitalOcean (الأقوى)**
- **الموقع:** https://www.digitalocean.com
- **السعر:** $4-6 شهرياً
- **المميزات:** قوية جداً، مستقرة

---

## **الخطوة 2: إعداد البوت للنشر**

### **أ) إنشاء ملف `requirements.txt`:**

```bash
pandas==2.0.0
numpy==1.24.0
python-binance==1.0.17
```

### **ب) إنشاء ملف `Procfile` (لـ Railway/Render):**

```
worker: python improved_equal_levels_bot.py
```

### **ج) إنشاء ملف `bot_runner.py`:**

```python
import os
import time
from improved_equal_levels_bot import EqualLevelsBot

# الحصول على مفاتيح Binance من متغيرات البيئة
API_KEY = os.getenv("BINANCE_API_KEY", "YOUR_API_KEY")
API_SECRET = os.getenv("BINANCE_API_SECRET", "YOUR_API_SECRET")

def main():
    print("🤖 بدء البوت على VPS...")
    
    bot = EqualLevelsBot(
        symbol="BTCUSDT",
        timeframe="1m",
        rr_ratio=2.0,
        volume_mult=1.5,
        risk_pct=0.005,
        lookback=50
    )
    
    # تشغيل البوت بشكل مستمر
    while True:
        try:
            bot.run(iterations=1000)
            print("✅ اكتمل دورة الاختبار، إعادة التشغيل...")
            time.sleep(60)
        except Exception as e:
            print(f"❌ خطأ: {e}")
            time.sleep(30)

if __name__ == "__main__":
    main()
```

---

## **الخطوة 3: نشر على Railway (الأسهل)**

### **الطريقة الأولى: من واجهة الويب**

1. **اذهب إلى:** https://railway.app
2. **سجل بـ GitHub** (أو Google)
3. **اضغط:** "New Project"
4. **اختر:** "Deploy from GitHub"
5. **اختر repository** يحتوي على البوت
6. **أضف متغيرات البيئة:**
   - اذهب إلى "Variables"
   - أضف:
     ```
     BINANCE_API_KEY=your_key_here
     BINANCE_API_SECRET=your_secret_here
     ```
7. **اضغط Deploy**

### **الطريقة الثانية: من سطر الأوامر**

```bash
# تثبيت Railway CLI
npm install -g @railway/cli

# تسجيل الدخول
railway login

# إنشاء project جديد
railway init

# نشر البوت
railway up
```

---

## **الخطوة 4: نشر على Render**

1. **اذهب إلى:** https://render.com
2. **سجل بـ GitHub**
3. **اضغط:** "New +"
4. **اختر:** "Web Service"
5. **اختر repository**
6. **ملء البيانات:**
   - **Name:** my-trading-bot
   - **Runtime:** Python 3
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `python bot_runner.py`
7. **أضف متغيرات البيئة:**
   - BINANCE_API_KEY
   - BINANCE_API_SECRET
8. **اضغط Deploy**

---

## **الخطوة 5: نشر على DigitalOcean**

### **الطريقة السهلة (App Platform):**

1. **اذهب إلى:** https://www.digitalocean.com
2. **سجل حساب جديد** (استخدم كود: ONWORKS لـ $100 مجاني)
3. **اذهب إلى:** Apps
4. **اضغط:** "Create App"
5. **اختر GitHub repository**
6. **اختر:**
   - **Name:** trading-bot
   - **Resource Type:** Worker
7. **أضف متغيرات البيئة**
8. **Deploy**

---

## **الخطوة 6: الحصول على مفاتيح Binance**

### **خطوات الحصول على API Keys:**

1. **اذهب إلى:** https://www.binance.com
2. **سجل حساب** (إذا لم تكن مسجل)
3. **اذهب إلى:** Settings → API Management
4. **اضغط:** "Create API"
5. **اختر:** "Spot Trading"
6. **انسخ:**
   - API Key
   - Secret Key
7. **احفظهما بأمان** (لا تشاركهما مع أحد)

---

## **الخطوة 7: المراقبة والتحديثات**

### **مراقبة البوت:**

```bash
# عرض السجلات (Logs)
railway logs

# أو على Render
# اذهب إلى Dashboard → Logs
```

### **إيقاف البوت:**

```bash
# على Railway
railway down

# أو من الواجهة
# اذهب إلى Dashboard → Suspend
```

---

## **الخطوة 8: الأمان والنصائح**

⚠️ **نصائح أمان مهمة:**

1. **لا تشارك مفاتيح API** مع أحد
2. **استخدم حسابات تجريبية** أولاً
3. **حدد حد أقصى للإنفاق** على Binance
4. **استخدم 2FA** على حسابك
5. **راجع السجلات بانتظام**

---

## **الخطوة 9: التكاليف المتوقعة**

| الخدمة | السعر | الملاحظات |
|--------|------|---------|
| **Railway** | مجاني - $5/شهر | الأفضل للمبتدئين |
| **Render** | مجاني - $7/شهر | موثوق |
| **DigitalOcean** | $4-6/شهر | قوي |
| **PythonAnywhere** | مجاني - $5/شهر | متخصص Python |

---

## **الخطوة 10: استكشاف الأخطاء**

### **المشكلة: البوت لا يبدأ**
```bash
# تحقق من السجلات
railway logs

# تأكد من requirements.txt
cat requirements.txt
```

### **المشكلة: خطأ في Binance API**
```
تأكد من:
1. مفاتيح API صحيحة
2. حسابك مفعّل على Binance
3. لديك رصيد كافي
```

### **المشكلة: البوت يتوقف**
```python
# أضف هذا في bot_runner.py
import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

try:
    # كود البوت
except Exception as e:
    logger.error(f"خطأ: {e}")
    # إعادة محاولة
```

---

## **الخطوة 11: الخطوات التالية**

بعد النشر:

1. ✅ **اختبر البوت** على حساب تجريبي أولاً
2. ✅ **راقب الأداء** يومياً
3. ✅ **حدّث الاستراتيجية** حسب النتائج
4. ✅ **أضف إشعارات** (Telegram/Email)

---

## **روابط مفيدة:**

- Railway: https://railway.app
- Render: https://render.com
- DigitalOcean: https://www.digitalocean.com
- Binance API: https://binance-docs.github.io/apidocs/
- PythonAnywhere: https://www.pythonanywhere.com

---

**هل تحتاج مساعدة في أي خطوة؟** 🚀
