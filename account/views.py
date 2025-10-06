import secrets
import logging
from datetime import timedelta
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.throttling import ScopedRateThrottle
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils import timezone
from kavenegar import KavenegarAPI
from django.conf import settings

from .serializers import RequestOTPSerializer, VerifyOTPSerializer, ProfileSerializer

User = get_user_model()
logger = logging.getLogger(__name__)

# OTP Configuration
OTP_EXPIRY_MINUTES = 5
MAX_OTP_ATTEMPTS = 3
LOCK_DURATION_MINUTES = 15


class RequestOTPView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = 'otp'
    
    def post(self, request):
        serializer = RequestOTPSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        phone_number = serializer.validated_data['phone_number']
        
        # Generate cryptographically secure OTP
        auth_code = secrets.randbelow(900000) + 100000
        
        user, created = User.objects.get_or_create(
            phone_number=phone_number,
            defaults={'is_active': False}
        )
        
        # Reset OTP fields
        user.auth_code = auth_code
        user.auth_code_created_at = timezone.now()
        user.auth_attempts = 0
        user.auth_locked_until = None
        user.save(update_fields=['auth_code', 'auth_code_created_at', 'auth_attempts', 'auth_locked_until'])
        
        # Send OTP via SMS
        try:
            api = KavenegarAPI(settings.KAVEH_NEGAR_API_KEY)
            api.verify_lookup({
                'receptor': phone_number,
                'token': str(auth_code),
                'template': 'users'
            })
            logger.info(f'کد OTP با موفقیت به شماره {phone_number} ارسال شد')
        except Exception as e:
            logger.exception(f'خطا در ارسال کد OTP به شماره {phone_number}: {str(e)}')
            # Continue even if SMS fails (for development/testing)
        
        return Response({'message': 'کد تایید ارسال شد'}, status=status.HTTP_200_OK)


class VerifyOTPView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = 'otp'
    
    def post(self, request):
        serializer = VerifyOTPSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        phone_number = serializer.validated_data['phone_number']
        code = serializer.validated_data['code']
        
        try:
            user = User.objects.get(phone_number=phone_number)
        except User.DoesNotExist:
            return Response({'error': 'اطلاعات ورود نامعتبر است'}, status=status.HTTP_400_BAD_REQUEST)
        
        # Check if account is locked
        if user.auth_locked_until and timezone.now() < user.auth_locked_until:
            remaining = (user.auth_locked_until - timezone.now()).seconds // 60
            return Response(
                {'error': f'حساب به مدت {remaining} دقیقه قفل شده است. لطفاً بعداً تلاش کنید'},
                status=status.HTTP_429_TOO_MANY_REQUESTS
            )
        
        # Check OTP expiry
        if not user.auth_code_created_at:
            return Response({'error': 'کد منقضی شده است. لطفاً کد جدید درخواست کنید'}, status=status.HTTP_400_BAD_REQUEST)
        
        otp_age = timezone.now() - user.auth_code_created_at
        if otp_age > timedelta(minutes=OTP_EXPIRY_MINUTES):
            # Clear expired OTP
            user.auth_code = None
            user.auth_code_created_at = None
            user.auth_attempts = 0
            user.save(update_fields=['auth_code', 'auth_code_created_at', 'auth_attempts'])
            return Response({'error': 'کد منقضی شده است. لطفاً کد جدید درخواست کنید'}, status=status.HTTP_400_BAD_REQUEST)
        
        # Verify code
        if user.auth_code != code:
            # Increment attempts
            user.auth_attempts += 1
            
            # Lock account if too many attempts
            if user.auth_attempts >= MAX_OTP_ATTEMPTS:
                user.auth_locked_until = timezone.now() + timedelta(minutes=LOCK_DURATION_MINUTES)
                user.save(update_fields=['auth_attempts', 'auth_locked_until'])
                return Response(
                    {'error': f'تعداد تلاش‌های نادرست بیش از حد مجاز. حساب برای {LOCK_DURATION_MINUTES} دقیقه قفل شد'},
                    status=status.HTTP_429_TOO_MANY_REQUESTS
                )
            
            user.save(update_fields=['auth_attempts'])
            remaining_attempts = MAX_OTP_ATTEMPTS - user.auth_attempts
            return Response(
                {'error': f'کد نادرست است. {remaining_attempts} تلاش باقی مانده'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Successful verification
        is_first_login = user.last_login is None
        
        with transaction.atomic():
            user.auth_code = None
            user.auth_code_created_at = None
            user.auth_attempts = 0
            user.auth_locked_until = None
            user.is_active = True
            user.last_login = timezone.now()
            user.save(update_fields=[
                'auth_code', 'auth_code_created_at', 'auth_attempts', 
                'auth_locked_until', 'is_active', 'last_login'
            ])
        
        # Send welcome message for first login
        if is_first_login:
            try:
                api = KavenegarAPI(settings.KAVEH_NEGAR_API_KEY)
                api.verify_lookup({
                    'receptor': phone_number,
                    'token': '',
                    'template': 'first-log'
                })
                logger.info(f'پیام خوش‌آمدگویی به شماره {phone_number} ارسال شد')
            except Exception as e:
                logger.exception(f'خطا در ارسال پیام خوش‌آمدگویی به شماره {phone_number}: {str(e)}')
        
        refresh = RefreshToken.for_user(user)
        
        return Response({
            'message': 'ورود موفق',
            'refresh': str(refresh),
            'access': str(refresh.access_token),
        }, status=status.HTTP_200_OK)


class ProfileView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        serializer = ProfileSerializer(request.user)
        return Response(serializer.data)
    
    def put(self, request):
        serializer = ProfileSerializer(request.user, data=request.data, partial=False)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        serializer.save()
        return Response(serializer.data)
    
    def patch(self, request):
        serializer = ProfileSerializer(request.user, data=request.data, partial=True)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        serializer.save()
        return Response(serializer.data)
