from unittest.mock import patch, MagicMock
from django.test import TestCase, override_settings
from django.urls import reverse
from django.conf import settings
from django.utils import timezone
from rest_framework.test import APIClient
from rest_framework import status
from django.contrib.auth import get_user_model

User = get_user_model()


@override_settings(
    KAVEH_NEGAR_API_KEY='test-api-key',
    REST_FRAMEWORK={
        'DEFAULT_THROTTLE_RATES': {
            'otp': '1000/min',
        }
    }
)
class OTPAuthTestCase(TestCase):
    def setUp(self):
        from django.core.cache import cache
        cache.clear()
        self.client = APIClient()
        self.register_url = reverse('request-otp')
        self.verify_url = reverse('verify-otp')
        self.profile_url = reverse('profile')
    
    @patch('account.views.KavenegarAPI')
    def test_request_otp_success(self, mock_kavenegar):
        mock_api = MagicMock()
        mock_kavenegar.return_value = mock_api

        data = {'phone_number': '09123456789'}
        response = self.client.post(self.register_url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('کد تایید ارسال شد', response.data['message'])

        user = User.objects.get(phone_number='09123456789')
        self.assertIsNotNone(user.auth_code)
        self.assertTrue(100000 <= user.auth_code <= 999999)

        mock_api.verify_lookup.assert_called_once()
        call_args = mock_api.verify_lookup.call_args[0][0]
        self.assertEqual(call_args['receptor'], '09123456789')
        self.assertEqual(call_args['template'], 'users')
        self.assertEqual(call_args['token'], str(user.auth_code))
        # KavenegarAPI باید با کلید تنظیمات صدا شده باشه
        mock_kavenegar.assert_called_once_with(settings.KAVEH_NEGAR_API_KEY)
    @patch('account.views.KavenegarAPI')
    def test_verify_otp_success(self, mock_kavenegar):
        mock_api = MagicMock()
        mock_kavenegar.return_value = mock_api

        user = User.objects.create(
            phone_number='09123456789', 
            auth_code=123456,
            auth_code_created_at=timezone.now()
        )

        data = {'phone_number': '09123456789', 'code': 123456}
        response = self.client.post(self.verify_url, data)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access', response.data)
        self.assertIn('refresh', response.data)
        self.assertIn('ورود موفق', response.data.get('message', ''))

        user.refresh_from_db()
        self.assertIsNone(user.auth_code)
        self.assertTrue(user.is_active)
        self.assertIsNotNone(user.last_login)
    @patch('account.views.KavenegarAPI')
    def test_verify_otp_first_login(self, mock_kavenegar):
        mock_api = MagicMock()
        mock_kavenegar.return_value = mock_api
        
        user = User.objects.create(
            phone_number='09123456789', 
            auth_code=123456,
            auth_code_created_at=timezone.now()
        )
        
        data = {'phone_number': '09123456789', 'code': 123456}
        response = self.client.post(self.verify_url, data)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Assert first-login welcome message was sent
        calls = mock_api.verify_lookup.call_args_list
        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0][0][0]['template'], 'first-log')
        self.assertEqual(calls[0][0][0]['receptor'], '09123456789')
        self.assertEqual(calls[0][0][0]['token'], '')
    
    @patch('account.views.KavenegarAPI')
    def test_verify_otp_second_login_no_first_log(self, mock_kavenegar):
        """Test that second login does NOT send first-log template"""
        mock_api = MagicMock()
        mock_kavenegar.return_value = mock_api
        
        # First login cycle: request OTP and verify
        self.client.post(self.register_url, {'phone_number': '09123456789'}, format='json')
        user = User.objects.get(phone_number='09123456789')
        first_code = user.auth_code
        response = self.client.post(self.verify_url, {'phone_number': '09123456789', 'code': first_code}, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Verify first-log was sent
        first_login_calls = [call for call in mock_api.verify_lookup.call_args_list 
                           if call[0][0].get('template') == 'first-log']
        self.assertEqual(len(first_login_calls), 1)
        
        # Reset mock for second login
        mock_api.verify_lookup.reset_mock()
        
        # Clear cache to avoid throttle issues
        from django.core.cache import cache
        cache.clear()
        
        # Second login cycle: request OTP again and verify
        otp_response = self.client.post(self.register_url, {'phone_number': '09123456789'}, format='json')
        self.assertEqual(otp_response.status_code, status.HTTP_200_OK)
        
        user.refresh_from_db()
        second_code = user.auth_code
        self.assertIsNotNone(second_code)
        self.assertIsNotNone(user.auth_code_created_at)
        
        response = self.client.post(self.verify_url, {'phone_number': '09123456789', 'code': second_code}, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Assert NO first-log message was sent for second login (only 'users' template for OTP request)
        second_login_calls = [call for call in mock_api.verify_lookup.call_args_list 
                            if call[0][0].get('template') == 'first-log']
        self.assertEqual(len(second_login_calls), 0)
    
    def test_verify_otp_wrong_code(self):
        user = User.objects.create(
            phone_number='09123456789', 
            auth_code=123456,
            auth_code_created_at=timezone.now()
        )
        
        data = {'phone_number': '09123456789', 'code': 654321}
        response = self.client.post(self.verify_url, data)
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('کد نادرست است', response.data['error'])
    
    def test_verify_otp_user_not_found(self):
        data = {'phone_number': '09123456789', 'code': 123456}
        response = self.client.post(self.verify_url, data)
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('اطلاعات ورود نامعتبر است', response.data['error'])
    
    def test_otp_expiry(self):
        """Test that expired OTP codes are rejected"""
        from datetime import timedelta
        
        # Create user with expired OTP
        user = User.objects.create(
            phone_number='09123456789',
            auth_code=123456,
            auth_code_created_at=timezone.now() - timedelta(minutes=10)
        )
        
        data = {'phone_number': '09123456789', 'code': 123456}
        response = self.client.post(self.verify_url, data)
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('منقضی', response.data['error'])
    
    def test_otp_attempt_limiting(self):
        """Test that account gets locked after max attempts"""
        user = User.objects.create(
            phone_number='09123456789',
            auth_code=123456,
            auth_code_created_at=timezone.now(),
            auth_attempts=0
        )
        
        # Try wrong code 3 times
        for i in range(3):
            response = self.client.post(self.verify_url, {
                'phone_number': '09123456789',
                'code': 999999
            })
            if i < 2:
                self.assertIn('کد نادرست است', response.data['error'])
        
        # Should be locked after 3 attempts
        self.assertEqual(response.status_code, status.HTTP_429_TOO_MANY_REQUESTS)
        self.assertIn('قفل', response.data['error'])
        
        user.refresh_from_db()
        self.assertIsNotNone(user.auth_locked_until)
    
    def test_profile_get(self):
        user = User.objects.create(phone_number='09123456789')
        self.client.force_authenticate(user=user)
        
        response = self.client.get(self.profile_url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['phone_number'], '09123456789')
    def test_profile_update(self):
        user = User.objects.create(phone_number='09123456789')
        self.client.force_authenticate(user=user)

        data = {'username': 'testuser', 'email': 'test@example.com'}
        response = self.client.put(self.profile_url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        user.refresh_from_db()
        self.assertEqual(user.username, 'testuser')
        self.assertEqual(user.email, 'test@example.com')
    
    @patch('account.views.KavenegarAPI')
    def test_phone_normalization_persian_digits(self, mock_kavenegar):
        """Test phone number normalization with Persian digits"""
        mock_api = MagicMock()
        mock_kavenegar.return_value = mock_api
        
        data = {'phone_number': '۰۹۱۲۳۴۵۶۷۸۹'}
        response = self.client.post(self.register_url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        user = User.objects.get(phone_number='09123456789')
        self.assertIsNotNone(user)
    
    @patch('account.views.KavenegarAPI')
    def test_phone_normalization_country_code(self, mock_kavenegar):
        """Test phone number normalization with +98 prefix"""
        mock_api = MagicMock()
        mock_kavenegar.return_value = mock_api
        
        data = {'phone_number': '+989123456789'}
        response = self.client.post(self.register_url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        user = User.objects.get(phone_number='09123456789')
        self.assertIsNotNone(user)
    
    @patch('account.views.KavenegarAPI')
    def test_phone_normalization_with_spaces(self, mock_kavenegar):
        """Test phone number normalization with spaces"""
        mock_api = MagicMock()
        mock_kavenegar.return_value = mock_api
        
        data = {'phone_number': '0912 345 6789'}
        response = self.client.post(self.register_url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        user = User.objects.get(phone_number='09123456789')
        self.assertIsNotNone(user)


@override_settings(
    KAVEH_NEGAR_API_KEY='test-api-key',
    REST_FRAMEWORK={
        'DEFAULT_THROTTLE_RATES': {
            'otp': '3/min',
        }
    }
)
class OTPThrottlingTestCase(TestCase):
    def setUp(self):
        from django.core.cache import cache
        cache.clear()
        self.client = APIClient()
        self.register_url = reverse('request-otp')
    
    @patch('account.views.KavenegarAPI')
    def test_otp_throttling(self, mock_kavenegar):
        mock_api = MagicMock()
        mock_kavenegar.return_value = mock_api

        data = {'phone_number': '09123456789'}

        for i in range(3):
            response = self.client.post(self.register_url, data, format='json')
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertIn('کد تایید ارسال شد', response.data.get('message', ''))

        response = self.client.post(self.register_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_429_TOO_MANY_REQUESTS)
        self.assertIn('throttled', str(response.data).lower())
