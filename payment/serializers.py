from rest_framework import serializers
from .models import Transaction, SubscriptionPlan, Subscription, SubscriptionTransaction


class TransactionSerializer(serializers.ModelSerializer):
    """سریالایزر تراکنش"""
    class Meta:
        model = Transaction
        fields = ['id', 'trans_id', 'amount', 'card_num', 'factor_id', 'status', 'created_at', 'updated_at']
        read_only_fields = ['id', 'trans_id', 'card_num', 'factor_id', 'status', 'created_at', 'updated_at']


class CreateTransactionSerializer(serializers.Serializer):
    """سریالایزر ایجاد تراکنش"""
    amount = serializers.IntegerField(min_value=1000)


class SubscriptionPlanSerializer(serializers.ModelSerializer):
    """سریالایزر پلن اشتراک"""
    class Meta:
        model = SubscriptionPlan
        fields = ['id', 'name', 'duration_days', 'price', 'currency', 'description', 'is_active']


class SubscriptionSerializer(serializers.ModelSerializer):
    """سریالایزر اشتراک"""
    plan = SubscriptionPlanSerializer(read_only=True)
    is_active = serializers.BooleanField(read_only=True)
    
    class Meta:
        model = Subscription
        fields = ['id', 'plan', 'start_date', 'end_date', 'is_active', 'created_at']


class SubscriptionTransactionSerializer(serializers.ModelSerializer):
    """سریالایزر تراکنش اشتراک"""
    plan = SubscriptionPlanSerializer(read_only=True)
    
    class Meta:
        model = SubscriptionTransaction
        fields = [
            'id', 'plan', 'amount', 'currency', 'status',
            'description', 'before_end_date', 'after_end_date',
            'created_at', 'updated_at'
        ]


class PurchaseSubscriptionSerializer(serializers.Serializer):
    """سریالایزر خرید اشتراک"""
    plan_id = serializers.IntegerField()
