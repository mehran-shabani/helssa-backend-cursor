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
        self.client.post(self.verify_url, {'phone_number': '09123456789', 'code': first_code}, format='json')
        
        # Reset mock for second login
        mock_api.verify_lookup.reset_mock()
        
        # Second login cycle: request OTP again and verify
        self.client.post(self.register_url, {'phone_number': '09123456789'}, format='json')
        user.refresh_from_db()
        second_code = user.auth_code
        self.client.post(self.verify_url, {'phone_number': '09123456789', 'code': second_code}, format='json')
        
        # Assert NO first-log message was sent for second login
        self.assertEqual(mock_api.verify_lookup.call_count, 0)
    
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
    def test_otp_throttling(self, mock_kavenegar):
        mock_api = MagicMock()
        mock_kavenegar.return_value = mock_api

        data = {'phone_number': '09123456789'}

        for i in range(3):
            response = self.client.post(self.register_url, data)
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertIn('کد تایید ارسال شد', response.data.get('message', ''))

        response = self.client.post(self.register_url, data)
        self.assertEqual(response.status_code, status.HTTP_429_TOO_MANY_REQUESTS)
        self.assertIn('throttled', str(response.data).lower())
