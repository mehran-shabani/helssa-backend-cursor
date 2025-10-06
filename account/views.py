import secrets
import logging
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


class RequestOTPView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = 'otp'
    
    def post(self, request):
        serializer = RequestOTPSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        phone_number = serializer.validated_data['phone_number']
        auth_code = random.randint(100000, 999999)
        
        user, created = User.objects.get_or_create(phone_number=phone_number)
        user.auth_code = auth_code
        user.save()
        
        try:
            api = KavenegarAPI(settings.KAVEH_NEGAR_API_KEY)
            api.verify_lookup({
                'receptor': phone_number,
                'token': str(auth_code),
                'template': 'users'
            })
        except Exception as e:
            logger.exception(f'خطا در ارسال کد OTP به شماره {phone_number}: {str(e)}')
        
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
            user = None
        
        if not user or user.auth_code != code:
            return Response({'error': 'اطلاعات ورود نامعتبر است'}, status=status.HTTP_400_BAD_REQUEST)
        
        is_first_login = user.last_login is None
        
        with transaction.atomic():
            user.auth_code = None
            user.is_active = True
            user.last_login = timezone.now()
            user.save(update_fields=['auth_code', 'is_active', 'last_login'])
        
        if is_first_login:
            try:
                api = KavenegarAPI(settings.KAVEH_NEGAR_API_KEY)
                api.verify_lookup({
                    'receptor': phone_number,
                    'token': '',
                    'template': 'first-log'
                })
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
