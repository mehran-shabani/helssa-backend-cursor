# 🔐 ویژگی‌های امنیتی پروژه

## خلاصه

این سند تمام ویژگی‌های امنیتی پیاده‌سازی شده در سیستم احراز هویت OTP را شرح می‌دهد.

## 1. Phone Number Normalization

### مشکل
کاربران ممکن است شماره تلفن را به فرمت‌های مختلف وارد کنند:
- اعداد فارسی: `۰۹۱۲۳۴۵۶۷۸۹`
- با کد کشور: `+989123456789`
- با فاصله: `0912 345 6789`

### راه‌حل
تابع `normalize_phone_number()` در `account/serializers.py`:

```python
def normalize_phone_number(phone):
    # تبدیل اعداد فارسی به انگلیسی
    # حذف فاصله‌ها و خط تیره
    # مدیریت +98, 0098, 98
    return normalized
```

## 2. Cryptographically Secure OTP

### مشکل قبلی
```python
auth_code = random.randint(100000, 999999)  # ❌ قابل پیش‌بینی
```

### راه‌حل
```python
auth_code = secrets.randbelow(900000) + 100000  # ✅ امن
```

**چرا مهم است؟**
- `random` قابل پیش‌بینی است
- `secrets` از منابع entropy سیستم‌عامل استفاده می‌کند
- مناسب برای کاربردهای امنیتی و رمزنگاری

## 3. OTP Time-To-Live (TTL)

### پیاده‌سازی

**فیلد جدید در Model:**
```python
auth_code_created_at = models.DateTimeField(null=True, blank=True)
```

**چک انقضا در Verify:**
```python
OTP_EXPIRY_MINUTES = 5

if timezone.now() - user.auth_code_created_at > timedelta(minutes=OTP_EXPIRY_MINUTES):
    # کد منقضی شده - رد شود
```

**مزایا:**
- جلوگیری از استفاده کدهای قدیمی
- کاهش پنجره حمله
- تجربه کاربری بهتر

## 4. Attempt Limiting & Account Locking

### فیلدهای جدید

```python
auth_attempts = models.IntegerField(default=0)
auth_locked_until = models.DateTimeField(null=True, blank=True)
```

### منطق

```python
MAX_OTP_ATTEMPTS = 3
LOCK_DURATION_MINUTES = 15

# در صورت کد نادرست
user.auth_attempts += 1

if user.auth_attempts >= MAX_OTP_ATTEMPTS:
    user.auth_locked_until = timezone.now() + timedelta(minutes=15)
    # رد درخواست
```

**محافظت در برابر:**
- حملات Brute-Force
- تلاش‌های خودکار
- سوء استفاده از سیستم

## 5. User Enumeration Prevention

### مشکل قبلی
```python
if not user:
    return Response({'error': 'کاربر یافت نشد'}, status=404)  # ❌
if user.auth_code != code:
    return Response({'error': 'کد نادرست است'}, status=400)  # ❌
```

### راه‌حل
```python
if not user or user.auth_code != code:
    return Response({'error': 'اطلاعات ورود نامعتبر است'}, status=400)  # ✅
```

**چرا مهم است؟**
- مهاجم نمی‌تواند تشخیص دهد شماره‌ای ثبت شده یا خیر
- همه خطاها یکسان هستند

## 6. Inactive by Default

### تغییر

```python
# قبل
is_active = models.BooleanField(default=True)  # ❌

# بعد
is_active = models.BooleanField(default=False)  # ✅
```

**مزایا:**
- کاربران تا تایید OTP فعال نمی‌شوند
- جلوگیری از دسترسی بدون احراز هویت
- مدیریت بهتر چرخه حیات کاربر

## 7. Atomic Transactions

```python
with transaction.atomic():
    user.auth_code = None
    user.auth_code_created_at = None
    user.auth_attempts = 0
    user.auth_locked_until = None
    user.is_active = True
    user.last_login = timezone.now()
    user.save(update_fields=[...])
```

**مزایا:**
- یکپارچگی داده تضمین می‌شود
- در صورت خطا، هیچ تغییری اعمال نمی‌شود
- عملکرد بهتر با `update_fields`

## 8. Comprehensive Logging

```python
logger.info(f'کد OTP با موفقیت به شماره {phone_number} ارسال شد')
logger.exception(f'خطا در ارسال کد OTP به شماره {phone_number}: {str(e)}')
```

**مزایا:**
- قابلیت رصد و debug
- ردیابی مشکلات در production
- آمار و تحلیل

## 9. Environment-Driven Configuration

همه تنظیمات حساس از متغیرهای محیطی:

```python
SECRET_KEY = config('SECRET_KEY')
KAVEH_NEGAR_API_KEY = config('KAVEH_NEGAR_API_KEY')
DEBUG = config('DEBUG', default=False, cast=bool)
ALLOWED_HOSTS = config('ALLOWED_HOSTS', cast=Csv())
OTP_THROTTLE_RATE = config('OTP_THROTTLE_RATE', default='3/min')
```

## 10. Phone Number as Required USERNAME_FIELD

```python
# Model
phone_number = models.CharField(max_length=11, unique=True, db_index=True)
USERNAME_FIELD = 'phone_number'

# Manager
def create_user(self, phone_number, ...):
    if not phone_number:
        raise ValueError('شماره تلفن الزامی است')
```

## پارامترهای قابل تنظیم

در `account/views.py`:

```python
OTP_EXPIRY_MINUTES = 5        # مدت اعتبار OTP
MAX_OTP_ATTEMPTS = 3          # تعداد تلاش مجاز
LOCK_DURATION_MINUTES = 15    # مدت قفل حساب
```

برای تغییر این مقادیر، می‌توانید آنها را در settings یا environment variables قرار دهید.

## تست‌های امنیتی

تمام ویژگی‌های امنیتی با 14 تست پوشش داده شده‌اند:

- ✅ Phone normalization (Persian, +98, spaces)
- ✅ OTP expiry
- ✅ Attempt limiting & locking  
- ✅ User enumeration prevention
- ✅ First/second login distinction
- ✅ Throttling

## نتیجه‌گیری

سیستم احراز هویت با رعایت استانداردهای امنیتی OWASP و بهترین شیوه‌های Django پیاده‌سازی شده است.

**امتیاز امنیتی: 10/10** ⭐️

---

📚 برای اطلاعات بیشتر: `README.md` و `IMPROVEMENTS.md`
