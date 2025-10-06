from django.urls import path
from .views import RequestOTPView, VerifyOTPView, ProfileView

urlpatterns = [
    path('auth/register/', RequestOTPView.as_view(), name='request-otp'),
    path('auth/verify/', VerifyOTPView.as_view(), name='verify-otp'),
    path('auth/profile/', ProfileView.as_view(), name='profile'),
]
