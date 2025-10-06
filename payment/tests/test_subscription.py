from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from datetime import timedelta
from rest_framework.test import APIClient
from rest_framework import status
from account.models import CustomUser
from payment.models import SubscriptionPlan, Subscription, SubscriptionTransaction


class SubscriptionTestCase(TestCase):
    """تست‌های اشتراک"""
    
    def setUp(self):
        self.client = APIClient()
        self.user = CustomUser.objects.create_user(
            phone_number='09123456789',
            password='testpass123'
        )
        self.user.is_active = True
        self.user.save()
        
        # ایجاد پلن‌های اشتراک
        self.plan_monthly = SubscriptionPlan.objects.create(
            name='ماهانه',
            duration_days=30,
            price=50000,
            currency='IRR',
            description='اشتراک ماهانه'
        )
        
        self.plan_yearly = SubscriptionPlan.objects.create(
            name='سالانه',
            duration_days=365,
            price=500000,
            currency='IRR',
            description='اشتراک سالانه'
        )
    
    def test_list_subscription_plans(self):
        """تست لیست پلن‌های اشتراک"""
        url = reverse('payment:subscription-plans')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(len(response.data), 2)
    
    def test_list_subscription_plans_only_active(self):
        """تست نمایش فقط پلن‌های فعال"""
        # غیرفعال کردن یک پلن
        self.plan_yearly.is_active = False
        self.plan_yearly.save()
        
        url = reverse('payment:subscription-plans')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # بررسی اینکه پلن غیرفعال در لیست نیست
        results = response.data.get('results', response.data)
        plan_names = [plan['name'] for plan in results]
        self.assertIn('ماهانه', plan_names)
        self.assertNotIn('سالانه', plan_names)
    
    def test_get_user_subscription_not_found(self):
        """تست دریافت اشتراک کاربر بدون اشتراک"""
        self.client.force_authenticate(user=self.user)
        url = reverse('payment:user-subscription')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
    
    def test_get_user_subscription_active(self):
        """تست دریافت اشتراک فعال کاربر"""
        # ایجاد اشتراک فعال
        subscription = Subscription.objects.create(
            user=self.user,
            plan=self.plan_monthly,
            start_date=timezone.now(),
            end_date=timezone.now() + timedelta(days=30)
        )
        
        self.client.force_authenticate(user=self.user)
        url = reverse('payment:user-subscription')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['plan']['name'], 'ماهانه')
        self.assertTrue(response.data['is_active'])
    
    def test_get_user_subscription_expired(self):
        """تست اشتراک منقضی شده"""
        # ایجاد اشتراک منقضی شده
        Subscription.objects.create(
            user=self.user,
            plan=self.plan_monthly,
            start_date=timezone.now() - timedelta(days=60),
            end_date=timezone.now() - timedelta(days=30)
        )
        
        self.client.force_authenticate(user=self.user)
        url = reverse('payment:user-subscription')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
    
    def test_purchase_subscription_new(self):
        """تست خرید اشتراک جدید"""
        self.client.force_authenticate(user=self.user)
        url = reverse('payment:purchase-subscription')
        data = {'plan_id': self.plan_monthly.id}
        
        response = self.client.post(url, data)
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        # بررسی ایجاد اشتراک
        subscription = Subscription.objects.get(user=self.user)
        self.assertEqual(subscription.plan, self.plan_monthly)
        self.assertTrue(subscription.is_active)
        
        # بررسی ایجاد SubscriptionTransaction
        sub_trans = SubscriptionTransaction.objects.get(user=self.user)
        self.assertEqual(sub_trans.status, 'SUCCESS')
        self.assertEqual(sub_trans.amount, self.plan_monthly.price)
        self.assertIsNone(sub_trans.before_end_date)
        self.assertIsNotNone(sub_trans.after_end_date)
    
    def test_purchase_subscription_renewal(self):
        """تست تمدید اشتراک موجود"""
        # ایجاد اشتراک فعلی
        current_end = timezone.now() + timedelta(days=10)
        current_subscription = Subscription.objects.create(
            user=self.user,
            plan=self.plan_monthly,
            start_date=timezone.now() - timedelta(days=20),
            end_date=current_end
        )
        
        self.client.force_authenticate(user=self.user)
        url = reverse('payment:purchase-subscription')
        data = {'plan_id': self.plan_yearly.id}
        
        response = self.client.post(url, data)
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        # بررسی تمدید اشتراک
        current_subscription.refresh_from_db()
        expected_end = current_end + timedelta(days=365)
        
        # بررسی تاریخ پایان (با اختلاف جزئی زمانی)
        self.assertAlmostEqual(
            current_subscription.end_date.timestamp(),
            expected_end.timestamp(),
            delta=2  # 2 second tolerance
        )
        
        # بررسی SubscriptionTransaction
        sub_trans = SubscriptionTransaction.objects.get(
            user=self.user,
            plan=self.plan_yearly
        )
        self.assertEqual(sub_trans.status, 'SUCCESS')
        self.assertIsNotNone(sub_trans.before_end_date)
        self.assertIsNotNone(sub_trans.after_end_date)
    
    def test_purchase_subscription_invalid_plan(self):
        """تست خرید با پلن نامعتبر"""
        self.client.force_authenticate(user=self.user)
        url = reverse('payment:purchase-subscription')
        data = {'plan_id': 9999}  # Invalid plan ID
        
        response = self.client.post(url, data)
        
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
    
    def test_purchase_subscription_inactive_plan(self):
        """تست خرید با پلن غیرفعال"""
        self.plan_monthly.is_active = False
        self.plan_monthly.save()
        
        self.client.force_authenticate(user=self.user)
        url = reverse('payment:purchase-subscription')
        data = {'plan_id': self.plan_monthly.id}
        
        response = self.client.post(url, data)
        
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
    
    def test_subscription_is_active_property(self):
        """تست property is_active"""
        # اشتراک فعال
        active_sub = Subscription.objects.create(
            user=self.user,
            plan=self.plan_monthly,
            start_date=timezone.now(),
            end_date=timezone.now() + timedelta(days=30)
        )
        self.assertTrue(active_sub.is_active)
        
        # اشتراک منقضی شده
        expired_sub = Subscription.objects.create(
            user=self.user,
            plan=self.plan_monthly,
            start_date=timezone.now() - timedelta(days=60),
            end_date=timezone.now() - timedelta(days=1)
        )
        self.assertFalse(expired_sub.is_active)
    
    def test_subscription_transaction_creation(self):
        """تست ایجاد SubscriptionTransaction"""
        sub_trans = SubscriptionTransaction.objects.create(
            user=self.user,
            plan=self.plan_monthly,
            amount=50000,
            currency='IRR',
            status='PENDING',
            description='تست خرید اشتراک'
        )
        
        self.assertEqual(sub_trans.user, self.user)
        self.assertEqual(sub_trans.plan, self.plan_monthly)
        self.assertEqual(sub_trans.status, 'PENDING')
        self.assertIsNotNone(sub_trans.id)  # UUID should be set
    
    def test_user_subscription_requires_authentication(self):
        """تست احراز هویت برای دریافت اشتراک"""
        url = reverse('payment:user-subscription')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
    
    def test_purchase_subscription_requires_authentication(self):
        """تست احراز هویت برای خرید اشتراک"""
        url = reverse('payment:purchase-subscription')
        data = {'plan_id': self.plan_monthly.id}
        response = self.client.post(url, data)
        
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
