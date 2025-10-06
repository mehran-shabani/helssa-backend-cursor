from unittest.mock import patch, Mock
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status
from account.models import CustomUser
from payment.models import Transaction


class BitPayIntegrationTestCase(TestCase):
    """تست‌های یکپارچگی BitPay"""
    
    def setUp(self):
        self.client = APIClient()
        self.user = CustomUser.objects.create_user(
            phone_number='09123456789',
            password='testpass123'
        )
        self.user.is_active = True
        self.user.save()
        self.client.force_authenticate(user=self.user)
    
    @patch('payment.views.requests.post')
    def test_create_transaction_success(self, mock_post):
        """تست ایجاد تراکنش موفق"""
        # Mock BitPay send response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'status': 1,
            'id_get': 'test_id_get_123'
        }
        mock_post.return_value = mock_response
        
        url = reverse('payment:create-transaction')
        data = {'amount': 10000}
        
        response = self.client.post(url, data)
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn('payment_url', response.data)
        self.assertIn('id_get', response.data)
        self.assertEqual(response.data['id_get'], 'test_id_get_123')
        
        # بررسی ایجاد تراکنش در دیتابیس
        transaction = Transaction.objects.get(card_num='test_id_get_123')
        self.assertEqual(transaction.user, self.user)
        self.assertEqual(transaction.amount, 10000)
        self.assertEqual(transaction.status, 'pending')
    
    @patch('payment.views.requests.post')
    def test_create_transaction_failed(self, mock_post):
        """تست ایجاد تراکنش ناموفق"""
        # Mock BitPay send response with error
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'status': 0,
            'message': 'Invalid API key'
        }
        mock_post.return_value = mock_response
        
        url = reverse('payment:create-transaction')
        data = {'amount': 10000}
        
        response = self.client.post(url, data)
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('error', response.data)
    
    @patch('payment.views.requests.post')
    def test_verify_payment_success(self, mock_post):
        """تست وریفای موفق پرداخت"""
        # ایجاد تراکنش pending
        transaction = Transaction.objects.create(
            user=self.user,
            amount=10000,
            card_num='test_id_get_456',
            status='pending'
        )
        
        # Mock BitPay verify response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'status': 1,
            'factorId': 'factor_123'
        }
        mock_post.return_value = mock_response
        
        url = reverse('payment:verify-payment')
        data = {
            'trans_id': 'trans_789',
            'id_get': 'test_id_get_456'
        }
        
        # AllowAny permission - no authentication needed
        self.client.force_authenticate(user=None)
        response = self.client.post(url, data)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('message', response.data)
        
        # بررسی بروزرسانی تراکنش
        transaction.refresh_from_db()
        self.assertEqual(transaction.status, 'successful')
        self.assertEqual(transaction.trans_id, 'trans_789')
        self.assertEqual(transaction.factor_id, 'factor_123')
    
    @patch('payment.views.requests.post')
    def test_verify_payment_already_verified(self, mock_post):
        """تست وریفای تراکنش قبلاً تایید شده"""
        transaction = Transaction.objects.create(
            user=self.user,
            amount=10000,
            card_num='test_id_get_789',
            status='pending'
        )
        
        # Mock BitPay verify response - status 11 means already verified
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'status': 11,
            'message': 'Transaction verified in the past'
        }
        mock_post.return_value = mock_response
        
        url = reverse('payment:verify-payment')
        data = {
            'trans_id': 'trans_999',
            'id_get': 'test_id_get_789'
        }
        
        self.client.force_authenticate(user=None)
        response = self.client.post(url, data)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('Transaction verified in the past', response.data['message'])
    
    @patch('payment.views.requests.post')
    def test_verify_payment_failed(self, mock_post):
        """تست وریفای ناموفق پرداخت"""
        transaction = Transaction.objects.create(
            user=self.user,
            amount=10000,
            card_num='test_id_get_fail',
            status='pending'
        )
        
        # Mock BitPay verify response with failure
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'status': 0,
            'message': 'Payment failed'
        }
        mock_post.return_value = mock_response
        
        url = reverse('payment:verify-payment')
        data = {
            'trans_id': 'trans_fail',
            'id_get': 'test_id_get_fail'
        }
        
        self.client.force_authenticate(user=None)
        response = self.client.post(url, data)
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        
        # بررسی بروزرسانی وضعیت
        transaction.refresh_from_db()
        self.assertEqual(transaction.status, 'failed')
    
    def test_verify_payment_missing_params(self):
        """تست وریفای با پارامترهای ناقص"""
        url = reverse('payment:verify-payment')
        data = {'trans_id': 'trans_123'}  # Missing id_get
        
        self.client.force_authenticate(user=None)
        response = self.client.post(url, data)
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
    
    def test_verify_payment_transaction_not_found(self):
        """تست وریفای با تراکنش موجود نبودن"""
        url = reverse('payment:verify-payment')
        data = {
            'trans_id': 'trans_not_exist',
            'id_get': 'id_not_exist'
        }
        
        self.client.force_authenticate(user=None)
        
        with patch('payment.views.requests.post') as mock_post:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {'status': 1}
            mock_post.return_value = mock_response
            
            response = self.client.post(url, data)
            
            self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
