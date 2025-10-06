import uuid
from django.db import models
from django.conf import settings
from django.utils import timezone


class Transaction(models.Model):
    """تراکنش‌های پرداخت BitPay"""
    STATUS_CHOICES = [
        ('pending', 'در انتظار'),
        ('successful', 'موفق'),
        ('failed', 'ناموفق'),
    ]
    
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='transactions',
        verbose_name='کاربر'
    )
    trans_id = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        verbose_name='شناسه تراکنش'
    )
    amount = models.IntegerField(verbose_name='مبلغ')
    card_num = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        db_index=True,
        verbose_name='شناسه درخواست (id_get)'
    )
    factor_id = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        verbose_name='شماره فاکتور'
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending',
        db_index=True,
        verbose_name='وضعیت'
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='تاریخ ایجاد')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='تاریخ بروزرسانی')
    
    class Meta:
        verbose_name = 'تراکنش'
        verbose_name_plural = 'تراکنش‌ها'
        indexes = [
            models.Index(fields=['status', 'created_at']),
            models.Index(fields=['user']),
        ]
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.user} - {self.amount} - {self.status}"


class SubscriptionPlan(models.Model):
    """پلن‌های اشتراک"""
    name = models.CharField(max_length=100, verbose_name='نام پلن')
    duration_days = models.IntegerField(verbose_name='مدت (روز)')
    price = models.IntegerField(verbose_name='قیمت')
    currency = models.CharField(max_length=10, default='IRR', verbose_name='واحد پول')
    description = models.TextField(blank=True, verbose_name='توضیحات')
    is_active = models.BooleanField(default=True, verbose_name='فعال')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='تاریخ ایجاد')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='تاریخ بروزرسانی')
    
    class Meta:
        verbose_name = 'پلن اشتراک'
        verbose_name_plural = 'پلن‌های اشتراک'
        ordering = ['price']
    
    def __str__(self):
        return f"{self.name} - {self.duration_days} روز"


class Subscription(models.Model):
    """اشتراک کاربران"""
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='subscriptions',
        verbose_name='کاربر'
    )
    plan = models.ForeignKey(
        SubscriptionPlan,
        on_delete=models.PROTECT,
        related_name='subscriptions',
        verbose_name='پلن'
    )
    start_date = models.DateTimeField(verbose_name='تاریخ شروع')
    end_date = models.DateTimeField(verbose_name='تاریخ پایان')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='تاریخ ایجاد')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='تاریخ بروزرسانی')
    
    class Meta:
        verbose_name = 'اشتراک'
        verbose_name_plural = 'اشتراک‌ها'
        indexes = [
            models.Index(fields=['user', 'end_date']),
        ]
        ordering = ['-created_at']
    
    @property
    def is_active(self):
        """بررسی فعال بودن اشتراک"""
        return self.end_date >= timezone.now()
    
    def __str__(self):
        return f"{self.user} - {self.plan.name}"


class SubscriptionTransaction(models.Model):
    """تراکنش‌های اشتراک"""
    STATUS_CHOICES = [
        ('PENDING', 'در انتظار'),
        ('SUCCESS', 'موفق'),
        ('FAILED', 'ناموفق'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='subscription_transactions',
        verbose_name='کاربر'
    )
    plan = models.ForeignKey(
        SubscriptionPlan,
        on_delete=models.PROTECT,
        verbose_name='پلن'
    )
    amount = models.IntegerField(verbose_name='مبلغ')
    currency = models.CharField(max_length=10, default='IRR', verbose_name='واحد پول')
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='PENDING',
        db_index=True,
        verbose_name='وضعیت'
    )
    description = models.TextField(blank=True, verbose_name='توضیحات')
    before_end_date = models.DateTimeField(null=True, blank=True, verbose_name='تاریخ انقضا قبل')
    after_end_date = models.DateTimeField(null=True, blank=True, verbose_name='تاریخ انقضا بعد')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='تاریخ ایجاد')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='تاریخ بروزرسانی')
    
    class Meta:
        verbose_name = 'تراکنش اشتراک'
        verbose_name_plural = 'تراکنش‌های اشتراک'
        indexes = [
            models.Index(fields=['user', 'status']),
            models.Index(fields=['status', 'created_at']),
        ]
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.user} - {self.plan.name} - {self.status}"
