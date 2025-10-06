from django.urls import path
from .views import (
    CreateTransactionAPIView,
    VerifyPaymentAPIView,
    SubscriptionPlanListAPIView,
    UserSubscriptionAPIView,
    PurchaseSubscriptionAPIView,
)

app_name = 'payment'

urlpatterns = [
    # تراکنش‌های پرداخت
    path('transaction/create/', CreateTransactionAPIView.as_view(), name='create-transaction'),
    path('verify/', VerifyPaymentAPIView.as_view(), name='verify-payment'),
    
    # اشتراک‌ها
    path('plans/', SubscriptionPlanListAPIView.as_view(), name='subscription-plans'),
    path('subscription/', UserSubscriptionAPIView.as_view(), name='user-subscription'),
    path('subscription/purchase/', PurchaseSubscriptionAPIView.as_view(), name='purchase-subscription'),
]
