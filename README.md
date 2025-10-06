# Django OTP Authentication Project

پروژه Django با احراز هویت OTP مبتنی بر Kavenegar

## 📋 ویژگی‌ها

- ✅ احراز هویت مبتنی بر OTP (کد یکبار مصرف)
- ✅ مدل کاربر سفارشی با شماره تلفن
- ✅ صدور توکن JWT (Access & Refresh)
- ✅ محدودسازی نرخ درخواست (Rate Limiting)
- ✅ پیام خوش‌آمدگویی در اولین ورود
- ✅ API های RESTful
- ✅ نرمال‌سازی شماره تلفن (فارسی، +98، فاصله)
- ✅ OTP امن با `secrets` module
- ✅ انقضای خودکار OTP (5 دقیقه)
- ✅ محدودیت تلاش و قفل حساب (3 تلاش / 15 دقیقه)

## 🚀 نصب و راه‌اندازی

### 1. نصب وابستگی‌ها

```bash
pip install -r requirements.txt
```

### 2. تنظیم متغیرهای محیطی

فایل `.env.example` را کپی کرده و به `.env` تغییر نام دهید:

```bash
cp .env.example .env
```

سپس مقادیر زیر را در فایل `.env` تنظیم کنید:

```env
SECRET_KEY=your-secret-key-here
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1
KAVEH_NEGAR_API_KEY=your-kavenegar-api-key
OTP_THROTTLE_RATE=3/min
```

**نکته:** برای تولید SECRET_KEY می‌توانید از دستور زیر استفاده کنید:

```bash
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

### 3. اجرای مایگریشن‌ها

```bash
python manage.py migrate
```

### 4. اجرای سرور

```bash
python manage.py runserver
```

## 📡 API Endpoints

### ثبت‌نام / درخواست کد OTP

```http
POST /api/auth/register/
Content-Type: application/json

{
  "phone_number": "09123456789"
}
```

**پاسخ:**
```json
{
  "message": "کد تایید ارسال شد"
}
```

### تایید کد OTP و دریافت توکن

```http
POST /api/auth/verify/
Content-Type: application/json

{
  "phone_number": "09123456789",
  "code": 123456
}
```

**پاسخ:**
```json
{
  "message": "ورود موفق",
  "refresh": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "access": "eyJ0eXAiOiJKV1QiLCJhbGc..."
}
```

### مشاهده پروفایل

```http
GET /api/auth/profile/
Authorization: Bearer {access_token}
```

### ویرایش کامل پروفایل (PUT)

```http
PUT /api/auth/profile/
Authorization: Bearer {access_token}
Content-Type: application/json

{
  "username": "example",
  "email": "user@example.com",
  "first_name": "نام",
  "last_name": "نام خانوادگی"
}
```

### ویرایش جزئی پروفایل (PATCH)

```http
PATCH /api/auth/profile/
Authorization: Bearer {access_token}
Content-Type: application/json

{
  "username": "new_username"
}
```

## 🧪 اجرای تست‌ها

```bash
python manage.py test account.tests
```

برای خروجی جزئی‌تر:

```bash
python manage.py test account.tests -v 2
```

## 🔒 امنیت

### تغییرات امنیتی اعمال شده:

1. **OTP Cryptographically Secure**: استفاده از `secrets` به جای `random` برای تولید کد
2. **OTP TTL (Time To Live)**: کدها پس از 5 دقیقه منقضی می‌شوند
3. **Attempt Limiting**: حداکثر 3 تلاش نادرست مجاز است
4. **Account Locking**: قفل خودکار حساب برای 15 دقیقه پس از تلاش‌های ناموفق
5. **جلوگیری از User Enumeration**: پیام‌های خطا برای شماره نامعتبر و کد اشتباه یکسان هستند
6. **لاگ استثناها**: همه خطاهای Kavenegar با جزئیات لاگ می‌شوند
7. **تراکنش‌های اتمیک**: تغییرات کاربر در یک تراکنش انجام می‌شوند
8. **متغیرهای محیطی**: تمام اطلاعات حساس از environment variables خوانده می‌شوند
9. **Rate Limiting**: محدودسازی درخواست OTP (پیش‌فرض: 3 درخواست در دقیقه)
10. **Phone Normalization**: پشتیبانی از اعداد فارسی، کدهای کشور (+98, 0098) و فاصله‌ها
11. **Inactive by Default**: کاربران تا تایید OTP غیرفعال هستند

### قبل از Production:

- ✅ `DEBUG=False` تنظیم کنید
- ✅ `SECRET_KEY` قوی و منحصر به فرد تولید کنید
- ✅ `ALLOWED_HOSTS` را با دامنه‌های واقعی تنظیم کنید
- ✅ از PostgreSQL یا MySQL به جای SQLite استفاده کنید
- ✅ HTTPS را فعال کنید
- ⚠️  در نظر داشته باشید که کتابخونه `kavenegar` از سال 2018 آپدیت نشده است

## ⚠️ نکات مهم

### کتابخونه Kavenegar

کتابخونه فعلی `kavenegar` (نسخه 1.1.2) از می 2018 آپدیت نشده است. گزینه‌های جایگزین:

1. **برای استفاده async**: `aio-kavenegar` (نسخه 2.0.1، ژانویه 2024)
2. **پیاده‌سازی دستی**: استفاده از `requests` یا `httpx` با API مستقیم Kavenegar
3. **سرویس دیگر**: مهاجرت به سرویس‌های فعال مانند Twilio

## 📂 ساختار پروژه

```
.
├── account/              # اپ احراز هویت
│   ├── migrations/
│   ├── tests/
│   ├── models.py        # مدل کاربر سفارشی
│   ├── serializers.py   # سریالایزرهای DRF
│   ├── views.py         # ویوهای API
│   └── urls.py          # URL routing
├── core/                # تنظیمات پروژه
│   ├── settings.py
│   └── urls.py
├── payment/             # اپ پرداخت (اسکلت)
├── telemedicine/        # اپ طب از راه دور (اسکلت)
├── .env.example         # نمونه فایل محیطی
├── .gitignore
├── requirements.txt
└── manage.py
```

## 🔧 تنظیمات پیشرفته

### تغییر نرخ Throttling

در فایل `.env`:

```env
OTP_THROTTLE_RATE=5/min  # 5 درخواست در دقیقه
OTP_THROTTLE_RATE=10/hour # 10 درخواست در ساعت
```

### تنظیم دیتابیس PostgreSQL

در فایل `.env`:

```env
DB_ENGINE=django.db.backends.postgresql
DB_NAME=your_database
DB_USER=your_user
DB_PASSWORD=your_password
DB_HOST=localhost
DB_PORT=5432
```

## 📝 مجوز

این پروژه تحت مجوز MIT منتشر شده است.

## 🤝 مشارکت

برای مشارکت در پروژه:

1. پروژه را Fork کنید
2. یک Branch جدید بسازید (`git checkout -b feature/amazing-feature`)
3. تغییرات خود را Commit کنید (`git commit -m 'Add amazing feature'`)
4. به Branch خود Push کنید (`git push origin feature/amazing-feature`)
5. یک Pull Request باز کنید

## 📞 پشتیبانی

در صورت وجود مشکل یا سوال، لطفاً یک Issue باز کنید.

---

**توجه**: این پروژه یک پایه اولیه است و برای استفاده در محیط production نیاز به پیکربندی‌های امنیتی بیشتر دارد.
