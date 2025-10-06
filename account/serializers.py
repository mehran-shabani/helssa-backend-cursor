from rest_framework import serializers
from django.contrib.auth import get_user_model

User = get_user_model()


class RequestOTPSerializer(serializers.Serializer):
    phone_number = serializers.CharField(max_length=11, required=True)
    
    def validate_phone_number(self, value):
        if not value.isdigit() or len(value) != 11:
            raise serializers.ValidationError('شماره تلفن باید ۱۱ رقم باشد')
        if not value.startswith('09'):
            raise serializers.ValidationError('شماره تلفن معتبر نیست')
        return value


class VerifyOTPSerializer(serializers.Serializer):
    phone_number = serializers.CharField(max_length=11, required=True)
    code = serializers.IntegerField(required=True)
    
    def validate_code(self, value):
        if not (100000 <= value <= 999999):
            raise serializers.ValidationError('کد باید ۶ رقم باشد')
        return value


class ProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('id', 'phone_number', 'username', 'email', 'first_name', 'last_name', 'date_joined')
        read_only_fields = ('id', 'phone_number', 'date_joined')
